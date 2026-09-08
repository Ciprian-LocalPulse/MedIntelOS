"""End-to-end OAuth + SMART-scope tests through the real FastAPI app.

Same locally generated RSA key approach as test_oauth.py, injected via
create_app's oauth_jwks_fetcher hook — no real identity provider needed.
"""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from medintelos.api.app import create_app
from medintelos.config import Settings

ISSUER = "https://issuer.example.test"
AUDIENCE = "medintelos-api"
KID = "test-key-1"
API_KEY = "test-key-with-sufficient-length"


@pytest.fixture(scope="module")
def keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def jwks(keypair):
    _, public_key = keypair
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk["kid"] = KID
    return {"keys": [jwk]}


def _token(keypair, *, scope: str) -> str:
    private_key, _ = keypair
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "patient-app-user",
        "scope": scope,
        "iat": now,
        "exp": now + 300,
    }
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": KID})


def _client(jwks_doc) -> TestClient:
    settings = Settings(
        environment="test",
        api_key=API_KEY,
        fhir_base_url="http://testserver",
        oauth_enabled=True,
        oauth_issuer=ISSUER,
        oauth_audience=AUDIENCE,
        oauth_jwks_url="https://issuer.example.test/jwks.json",
        rate_limit_requests_per_minute=600,
        rate_limit_burst=50,
    )
    return TestClient(create_app(settings, oauth_jwks_fetcher=lambda: jwks_doc))


def test_read_scope_allows_get_but_not_post(keypair, jwks):
    token = _token(keypair, scope="patient/Patient.read")
    headers = {"Authorization": f"Bearer {token}"}

    with _client(jwks) as api:
        create = api.post(
            "/fhir/R5/Patient",
            headers=headers,
            json={"resourceType": "Patient", "active": True},
        )
        assert create.status_code == 403

        # Seed a patient via the trusted API-key path so the read-scope
        # check below is exercised in isolation from the write check above.
        seeded = api.post(
            "/fhir/R5/Patient",
            headers={"X-API-Key": API_KEY},
            json={"resourceType": "Patient", "id": "scope-test-1", "active": True},
        )
        assert seeded.status_code == 201

        read = api.get("/fhir/R5/Patient/scope-test-1", headers=headers)
        assert read.status_code == 200


def test_wildcard_scope_allows_read_and_write(keypair, jwks):
    token = _token(keypair, scope="patient/*.*")
    headers = {"Authorization": f"Bearer {token}"}

    with _client(jwks) as api:
        created = api.post(
            "/fhir/R5/Patient",
            headers=headers,
            json={"resourceType": "Patient", "id": "scope-test-2", "active": True},
        )
        assert created.status_code == 201

        read = api.get("/fhir/R5/Patient/scope-test-2", headers=headers)
        assert read.status_code == 200


def test_scope_for_wrong_resource_type_is_rejected(keypair, jwks):
    token = _token(keypair, scope="patient/Observation.read")
    headers = {"Authorization": f"Bearer {token}"}

    with _client(jwks) as api:
        response = api.get("/fhir/R5/Patient?_count=10", headers=headers)
        assert response.status_code == 403


def test_invalid_bearer_token_is_401(jwks):
    with _client(jwks) as api:
        response = api.get(
            "/fhir/R5/Patient/whatever", headers={"Authorization": "Bearer not-a-real-jwt"}
        )
        assert response.status_code == 401


def test_missing_bearer_scheme_is_401(jwks):
    with _client(jwks) as api:
        response = api.get(
            "/fhir/R5/Patient/whatever", headers={"Authorization": "not-bearer-format"}
        )
        assert response.status_code == 401


def test_api_key_still_bypasses_scope_checks_when_oauth_enabled(jwks):
    with _client(jwks) as api:
        created = api.post(
            "/fhir/R5/Patient",
            headers={"X-API-Key": API_KEY},
            json={"resourceType": "Patient", "id": "scope-test-3", "active": True},
        )
        assert created.status_code == 201


def test_oauth_actor_is_recorded_distinctly_in_audit(keypair, jwks):
    token = _token(keypair, scope="patient/*.*")
    with _client(jwks) as api:
        api.post(
            "/fhir/R5/Patient",
            headers={"Authorization": f"Bearer {token}"},
            json={"resourceType": "Patient", "id": "scope-test-4", "active": True},
        )
        audit = api.get("/api/v1/audit", headers={"X-API-Key": API_KEY})
        actors = {entry["actor"] for entry in audit.json()["entries"]}
        assert "oauth:patient-app-user" in actors
