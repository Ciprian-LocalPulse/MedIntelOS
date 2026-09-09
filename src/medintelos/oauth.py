"""OAuth2/OIDC bearer-token authentication.

Validates `Authorization: Bearer <jwt>` against a JWKS endpoint (RS256 only —
this is a reference implementation, not a general-purpose JOSE library).
Alongside, not instead of, the existing API-key path in security.py; see
api/auth.py for how the two are combined.

The JWKS fetch is injectable (`jwks_fetcher`) specifically so this module is
unit-testable against a locally generated RSA keypair, without a real
identity provider — see tests/test_oauth.py.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from medintelos.config import Settings
from medintelos.oauth_exceptions import OAuthError, OAuthPrincipal

JWKSFetcher = Callable[[], dict[str, Any]]


class _JWKSCache:
    """Caches the JWKS document for `cache_seconds`, with a rate-limited
    forced refresh when a token's `kid` isn't found in the cached set (to
    tolerate normal key rotation without hammering the JWKS endpoint on
    every request bearing an unknown or malicious `kid`).
    """

    def __init__(self, fetcher: JWKSFetcher, cache_seconds: int) -> None:
        self._fetcher = fetcher
        self._cache_seconds = cache_seconds
        self._lock = threading.Lock()
        self._keys: dict[str, Any] = {}
        self._fetched_at: float = 0.0
        self._min_refresh_interval = 5.0

    def get_key(self, kid: str | None) -> Any:
        with self._lock:
            now = time.monotonic()
            stale = now - self._fetched_at > self._cache_seconds
            missing = kid is not None and kid not in self._keys
            can_force_refresh = now - self._fetched_at > self._min_refresh_interval
            if self._fetched_at == 0.0 or stale or (missing and can_force_refresh):
                self._refresh()
            if kid is None:
                if len(self._keys) == 1:
                    return next(iter(self._keys.values()))
                raise OAuthError("Token header is missing 'kid' and JWKS has multiple keys")
            try:
                return self._keys[kid]
            except KeyError as exc:
                raise OAuthError(f"No JWKS key found for kid={kid!r}") from exc

    def _refresh(self) -> None:
        document = self._fetcher()
        keys: dict[str, Any] = {}
        for jwk in document.get("keys", []):
            kid = jwk.get("kid")
            if kid is None:
                continue
            keys[kid] = RSAAlgorithm.from_jwk(jwk)
        self._keys = keys
        self._fetched_at = time.monotonic()


def _default_fetcher(jwks_url: str, timeout_seconds: float = 5.0) -> JWKSFetcher:
    def fetch() -> dict[str, Any]:
        response = httpx.get(jwks_url, timeout=timeout_seconds)
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    return fetch


class OIDCAuthenticator:
    """FastAPI dependency validating a bearer JWT against `settings`.

    `jwks_fetcher` defaults to fetching `settings.oauth_jwks_url` over HTTP;
    tests inject a fetcher backed by a locally generated key so no network
    access or real identity provider is required.
    """

    def __init__(self, settings: Settings, jwks_fetcher: JWKSFetcher | None = None) -> None:
        if not settings.oauth_issuer or not settings.oauth_audience or not settings.oauth_jwks_url:
            raise ValueError("OIDCAuthenticator requires issuer, audience, and jwks_url")
        self._issuer = settings.oauth_issuer
        self._audience = settings.oauth_audience
        fetcher = jwks_fetcher or _default_fetcher(settings.oauth_jwks_url)
        self._jwks = _JWKSCache(fetcher, settings.oauth_jwks_cache_seconds)

    def authenticate(self, token: str) -> OAuthPrincipal:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise OAuthError("Malformed token header") from exc

        if header.get("alg") != "RS256":
            raise OAuthError("Only RS256-signed tokens are accepted")

        key = self._jwks.get_key(header.get("kid"))

        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.InvalidTokenError as exc:
            raise OAuthError(f"Token validation failed: {exc}") from exc

        scope_claim = claims.get("scope", "")
        scopes = frozenset(scope_claim.split()) if scope_claim else frozenset()
        fhir_user = claims.get("fhirUser")
        launch_patient = claims.get("patient")
        return OAuthPrincipal(
            subject=str(claims["sub"]),
            scopes=scopes,
            claims=claims,
            fhir_user=str(fhir_user) if fhir_user else None,
            launch_patient=str(launch_patient) if launch_patient else None,
        )


__all__ = ["OAuthError", "OAuthPrincipal", "OIDCAuthenticator"]
