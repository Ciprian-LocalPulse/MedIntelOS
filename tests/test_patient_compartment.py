from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from medintelos.api.app import create_app
from medintelos.api.auth import AuthContext, patient_compartment_permits
from medintelos.config import Settings

ISSUER = "https://issuer.example.test"
AUDIENCE = "medintelos-api"
KID = "test-key-1"
API_KEY = "test-key-with-sufficient-length"


# -- unit tests for patient_compartment_permits ------------------------------


def _auth(launch_patient: str | None) -> AuthContext:
    return AuthContext(
        actor="oauth:test-user",
        auth_method="oauth",
        scopes=frozenset({"patient/*.*"}),
        full_access=False,
        launch_patient=launch_patient,
    )


def test_no_launch_patient_means_unrestricted():
    auth = _auth(None)
    assert patient_compartment_permits(auth, "Patient", {"id": "someone-else"})


def test_patient_resource_must_match_id():
    auth = _auth("p1")
    assert patient_compartment_permits(auth, "Patient", {"id": "p1"})
    assert not patient_compartment_permits(auth, "Patient", {"id": "p2"})


def test_subject_reference_must_match():
    auth = _auth("p1")
    matching = {"subject": {"reference": "Patient/p1"}}
    other = {"subject": {"reference": "Patient/p2"}}
    assert patient_compartment_permits(auth, "Observation", matching)
    assert not patient_compartment_permits(auth, "Observation", other)


def test_resource_without_subject_is_unrestricted():
    auth = _auth("p1")
    assert patient_compartment_permits(auth, "Device", {"id": "device-1"})


def test_api_key_full_access_never_restricted_by_compartment_logic():
    # full_access is what actually bypasses everything in app.py's routes;
    # this just confirms launch_patient is None (as it always is for
    # api-key auth), so patient_compartment_permits would be a no-op anyway.
    auth = AuthContext(
        actor="api-key-client", auth_method="api-key", scopes=frozenset(), full_access=True
    )
    assert auth.launch_patient is None


# -- end-to-end tests through the real API -----------------------------------


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


def _token(keypair, *, launch_patient: str) -> str:
    private_key, _ = keypair
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "app-user",
        "scope": "patient/*.*",
        "patient": launch_patient,
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


def test_launch_scoped_token_can_read_its_own_patient(keypair, jwks):
    with _client(jwks) as api:
        api.post(
            "/fhir/R5/Patient",
            headers={"X-API-Key": API_KEY},
            json={"resourceType": "Patient", "id": "compartment-1", "active": True},
        )
        token = _token(keypair, launch_patient="compartment-1")
        response = api.get(
            "/fhir/R5/Patient/compartment-1", headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 200


def test_launch_scoped_token_cannot_read_a_different_patient(keypair, jwks):
    with _client(jwks) as api:
        api.post(
            "/fhir/R5/Patient",
            headers={"X-API-Key": API_KEY},
            json={"resourceType": "Patient", "id": "compartment-2", "active": True},
        )
        token = _token(keypair, launch_patient="someone-else-entirely")
        response = api.get(
            "/fhir/R5/Patient/compartment-2", headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 403


def test_launch_scoped_search_filters_out_other_patients_observations(keypair, jwks):
    with _client(jwks) as api:
        api.post(
            "/fhir/R5/Observation",
            headers={"X-API-Key": API_KEY},
            json={
                "resourceType": "Observation",
                "id": "obs-mine",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
                "subject": {"reference": "Patient/compartment-3"},
            },
        )
        api.post(
            "/fhir/R5/Observation",
            headers={"X-API-Key": API_KEY},
            json={
                "resourceType": "Observation",
                "id": "obs-not-mine",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
                "subject": {"reference": "Patient/compartment-4"},
            },
        )
        token = _token(keypair, launch_patient="compartment-3")
        response = api.get(
            "/fhir/R5/Observation?_count=50", headers={"Authorization": f"Bearer {token}"}
        )
    ids = [entry["resource"]["id"] for entry in response.json().get("entry", [])]
    assert ids == ["obs-mine"]


def test_api_key_is_never_compartment_restricted(keypair, jwks):
    with _client(jwks) as api:
        seeded = api.post(
            "/fhir/R5/Patient",
            headers={"X-API-Key": API_KEY},
            json={"resourceType": "Patient", "id": "compartment-5", "active": True},
        )
        read = api.get("/fhir/R5/Patient/compartment-5", headers={"X-API-Key": API_KEY})
    assert seeded.status_code == 201
    assert read.status_code == 200
