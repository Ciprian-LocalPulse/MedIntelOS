from __future__ import annotations

import json
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from medintelos.api.app import create_app
from medintelos.config import Settings

API_KEY = "test-key-with-sufficient-length"
HEADERS = {"X-API-Key": API_KEY}
ASYNC_HEADERS = {**HEADERS, "Prefer": "respond-async"}


def client() -> TestClient:
    settings = Settings(environment="test", api_key=API_KEY, fhir_base_url="http://testserver")
    return TestClient(create_app(settings))


def _seed_patient(api: TestClient, patient_id: str) -> None:
    api.post(
        "/fhir/R5/Patient",
        headers=HEADERS,
        json={"resourceType": "Patient", "id": patient_id, "active": True},
    )


def test_kickoff_requires_prefer_respond_async_header() -> None:
    with client() as api:
        response = api.get("/fhir/R5/Patient/$export", headers=HEADERS)
    assert response.status_code == 400


def test_type_level_export_full_flow() -> None:
    with client() as api:
        _seed_patient(api, "export-1")
        _seed_patient(api, "export-2")

        kickoff = api.get("/fhir/R5/Patient/$export", headers=ASYNC_HEADERS)
        assert kickoff.status_code == 202
        status_url = kickoff.headers["Content-Location"]
        job_id = status_url.rsplit("/", 1)[-1]

        status_response = api.get(f"/fhir/R5/$export-status/{job_id}", headers=HEADERS)
        assert status_response.status_code == 200
        manifest = status_response.json()
        assert manifest["output"][0]["type"] == "Patient"
        assert manifest["output"][0]["count"] == 2

        file_url = manifest["output"][0]["url"]
        file_path = file_url.split("http://testserver", 1)[-1]
        ndjson_response = api.get(file_path, headers=HEADERS)

    assert ndjson_response.status_code == 200
    assert ndjson_response.headers["content-type"].startswith("application/fhir+ndjson")
    lines = ndjson_response.text.strip().split("\n")
    assert len(lines) == 2
    ids = {json.loads(line)["id"] for line in lines}
    assert ids == {"export-1", "export-2"}


def test_type_level_export_only_includes_requested_type() -> None:
    with client() as api:
        _seed_patient(api, "export-3")
        api.post(
            "/fhir/R5/Observation",
            headers=HEADERS,
            json={
                "resourceType": "Observation",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
            },
        )
        kickoff = api.get("/fhir/R5/Patient/$export", headers=ASYNC_HEADERS)
        job_id = kickoff.headers["Content-Location"].rsplit("/", 1)[-1]
        manifest = api.get(f"/fhir/R5/$export-status/{job_id}", headers=HEADERS).json()

    types = [output["type"] for output in manifest["output"]]
    assert types == ["Patient"]


def test_system_export_spans_multiple_resource_types() -> None:
    with client() as api:
        _seed_patient(api, "export-4")
        api.post(
            "/fhir/R5/Observation",
            headers=HEADERS,
            json={
                "resourceType": "Observation",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
            },
        )
        kickoff = api.get("/fhir/R5/$export", headers=ASYNC_HEADERS)
        assert kickoff.status_code == 202
        job_id = kickoff.headers["Content-Location"].rsplit("/", 1)[-1]
        manifest = api.get(f"/fhir/R5/$export-status/{job_id}", headers=HEADERS).json()

    types = {output["type"] for output in manifest["output"]}
    assert types == {"Patient", "Observation"}


def test_system_export_empty_resource_types_are_omitted() -> None:
    with client() as api:
        kickoff = api.get("/fhir/R5/$export", headers=ASYNC_HEADERS)
        job_id = kickoff.headers["Content-Location"].rsplit("/", 1)[-1]
        manifest = api.get(f"/fhir/R5/$export-status/{job_id}", headers=HEADERS).json()

    assert manifest["output"] == []


def test_export_status_404_for_unknown_job() -> None:
    with client() as api:
        response = api.get(
            "/fhir/R5/$export-status/00000000-0000-0000-0000-000000000000", headers=HEADERS
        )
    assert response.status_code == 404


def test_export_file_404_for_unknown_job() -> None:
    with client() as api:
        response = api.get(
            "/fhir/R5/$export-files/00000000-0000-0000-0000-000000000000/Patient.ndjson",
            headers=HEADERS,
        )
    assert response.status_code == 404


def test_export_file_404_for_resource_type_not_in_job() -> None:
    with client() as api:
        _seed_patient(api, "export-5")
        kickoff = api.get("/fhir/R5/Patient/$export", headers=ASYNC_HEADERS)
        job_id = kickoff.headers["Content-Location"].rsplit("/", 1)[-1]
        response = api.get(f"/fhir/R5/$export-files/{job_id}/Observation.ndjson", headers=HEADERS)
    assert response.status_code == 404


def test_cancel_export_removes_the_job() -> None:
    with client() as api:
        _seed_patient(api, "export-6")
        kickoff = api.get("/fhir/R5/Patient/$export", headers=ASYNC_HEADERS)
        job_id = kickoff.headers["Content-Location"].rsplit("/", 1)[-1]

        cancel = api.delete(f"/fhir/R5/$export-status/{job_id}", headers=HEADERS)
        assert cancel.status_code == 202

        status_after_cancel = api.get(f"/fhir/R5/$export-status/{job_id}", headers=HEADERS)
    assert status_after_cancel.status_code == 404


def test_export_kickoff_and_status_require_authentication() -> None:
    with client() as api:
        kickoff = api.get("/fhir/R5/Patient/$export", headers={"Prefer": "respond-async"})
        assert kickoff.status_code == 401

        status_response = api.get("/fhir/R5/$export-status/00000000-0000-0000-0000-000000000000")
        assert status_response.status_code == 401


def test_export_kickoff_is_recorded_in_audit() -> None:
    with client() as api:
        _seed_patient(api, "export-7")
        api.get("/fhir/R5/Patient/$export", headers=ASYNC_HEADERS)
        audit = api.get("/api/v1/audit", headers=HEADERS)
    actions = [entry["action"] for entry in audit.json()["entries"]]
    assert "fhir.export.kickoff" in actions


def test_system_export_rejects_oauth_scoped_clients() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk["kid"] = "k1"
    jwks_doc = {"keys": [jwk]}

    now = int(time.time())
    token = jwt.encode(
        {
            "iss": "https://issuer.example.test",
            "aud": "medintelos-api",
            "sub": "app-user",
            "scope": "patient/*.*",
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "k1"},
    )

    settings = Settings(
        environment="test",
        api_key=API_KEY,
        fhir_base_url="http://testserver",
        oauth_enabled=True,
        oauth_issuer="https://issuer.example.test",
        oauth_audience="medintelos-api",
        oauth_jwks_url="https://issuer.example.test/jwks.json",
    )
    with TestClient(
        create_app(settings, oauth_jwks_fetcher=lambda: jwks_doc)
    ) as api:
        response = api.get(
            "/fhir/R5/$export",
            headers={"Authorization": f"Bearer {token}", "Prefer": "respond-async"},
        )
    assert response.status_code == 403
