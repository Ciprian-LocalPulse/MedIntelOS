from fastapi.testclient import TestClient

from medintelos.api.app import create_app
from medintelos.config import Settings

API_KEY = "test-key-with-sufficient-length"


def client() -> TestClient:
    settings = Settings(environment="test", api_key=API_KEY, fhir_base_url="http://testserver")
    return TestClient(create_app(settings))


def test_health_and_authentication() -> None:
    with client() as api:
        assert api.get("/health").status_code == 200
        assert api.get("/fhir/R5/Patient/p1").status_code == 401


def test_fhir_crud_and_audit() -> None:
    headers = {"X-API-Key": API_KEY}
    patient = {"resourceType": "Patient", "id": "p1", "active": True}

    with client() as api:
        created = api.post("/fhir/R5/Patient", headers=headers, json=patient)
        read = api.get("/fhir/R5/Patient/p1", headers=headers)
        search = api.get("/fhir/R5/Patient?_count=10", headers=headers)
        audit = api.get("/api/v1/audit", headers=headers)

    assert created.status_code == 201
    assert read.status_code == 200
    assert search.json()["resourceType"] == "Bundle"
    assert audit.json()["chain_valid"] is True
    assert len(audit.json()["entries"]) == 3


def test_cdss_endpoint() -> None:
    payload = {
        "hook": "patient-view",
        "context": {
            "patient_id": "synthetic-1",
            "age": 70,
            "sex": "M",
            "vitals": {
                "systolic_bp": 88,
                "respiratory_rate": 26,
                "gcs": 13,
                "spo2": 91,
                "heart_rate": 115,
                "temperature": 39.1
            }
        }
    }

    with client() as api:
        response = api.post(
            "/api/v1/cdss/evaluate",
            headers={"X-API-Key": API_KEY},
            json=payload,
        )

    assert response.status_code == 200
    assert response.json()["cards"]
