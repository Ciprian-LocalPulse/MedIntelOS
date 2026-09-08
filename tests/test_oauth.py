"""Tests for OIDCAuthenticator.

Uses a locally generated RSA keypair and a hand-built JWKS document instead
of a real identity provider: `jwks_fetcher` is injected directly, so these
tests never touch the network and never depend on Keycloak/Auth0/etc. being
available.
"""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from medintelos.config import Settings
from medintelos.oauth import OIDCAuthenticator
from medintelos.oauth_exceptions import OAuthError

ISSUER = "https://issuer.example.test"
AUDIENCE = "medintelos-api"
KID = "test-key-1"


@pytest.fixture(scope="module")
def keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def jwks(keypair):
    _, public_key = keypair
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk["kid"] = KID
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return {"keys": [jwk]}


def _sign(keypair, *, claims_override=None, headers_override=None) -> str:
    private_key, _ = keypair
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-123",
        "scope": "patient/*.read",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(claims_override or {})
    headers = {"kid": KID}
    headers.update(headers_override or {})
    return jwt.encode(claims, private_key, algorithm="RS256", headers=headers)


def _authenticator(jwks_doc) -> OIDCAuthenticator:
    settings = Settings(
        oauth_enabled=True,
        oauth_issuer=ISSUER,
        oauth_audience=AUDIENCE,
        oauth_jwks_url="https://issuer.example.test/jwks.json",
    )
    return OIDCAuthenticator(settings, jwks_fetcher=lambda: jwks_doc)


def test_valid_token_is_accepted(keypair, jwks):
    token = _sign(keypair)
    principal = _authenticator(jwks).authenticate(token)
    assert principal.subject == "user-123"
    assert principal.scopes == {"patient/*.read"}


def test_wrong_audience_is_rejected(keypair, jwks):
    token = _sign(keypair, claims_override={"aud": "someone-else"})
    with pytest.raises(OAuthError):
        _authenticator(jwks).authenticate(token)


def test_wrong_issuer_is_rejected(keypair, jwks):
    token = _sign(keypair, claims_override={"iss": "https://not-the-issuer.test"})
    with pytest.raises(OAuthError):
        _authenticator(jwks).authenticate(token)


def test_expired_token_is_rejected(keypair, jwks):
    now = int(time.time())
    token = _sign(keypair, claims_override={"iat": now - 600, "exp": now - 300})
    with pytest.raises(OAuthError):
        _authenticator(jwks).authenticate(token)


def test_unknown_kid_is_rejected(keypair, jwks):
    token = _sign(keypair, headers_override={"kid": "no-such-key"})
    with pytest.raises(OAuthError, match="No JWKS key found"):
        _authenticator(jwks).authenticate(token)


def test_token_signed_by_a_different_key_is_rejected(jwks):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _sign((other_key, other_key.public_key()), headers_override={"kid": KID})
    with pytest.raises(OAuthError):
        _authenticator(jwks).authenticate(token)


def test_non_rs256_algorithm_is_rejected(keypair, jwks):
    # alg confusion: refuse anything that isn't RS256, even if it otherwise
    # decodes (e.g. an attacker resubmitting an HS256 token signed with a
    # guessed or leaked symmetric secret).
    token = jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "sub": "x"}, "some-secret", algorithm="HS256")
    with pytest.raises(OAuthError, match="RS256"):
        _authenticator(jwks).authenticate(token)


def test_missing_scope_claim_yields_empty_scopes(keypair, jwks):
    token = _sign(keypair, claims_override={"scope": ""})
    principal = _authenticator(jwks).authenticate(token)
    assert principal.scopes == frozenset()


def test_jwks_is_cached_across_calls(keypair, jwks):
    calls = {"count": 0}

    def counting_fetcher():
        calls["count"] += 1
        return jwks

    settings = Settings(
        oauth_enabled=True,
        oauth_issuer=ISSUER,
        oauth_audience=AUDIENCE,
        oauth_jwks_url="https://issuer.example.test/jwks.json",
        oauth_jwks_cache_seconds=300,
    )
    authenticator = OIDCAuthenticator(settings, jwks_fetcher=counting_fetcher)
    token = _sign(keypair)

    authenticator.authenticate(token)
    authenticator.authenticate(token)
    authenticator.authenticate(token)

    assert calls["count"] == 1
