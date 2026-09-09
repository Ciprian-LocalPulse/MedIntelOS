from fastapi.testclient import TestClient

from medintelos.api.app import create_app
from medintelos.config import Settings

API_KEY = "test-key-with-sufficient-length"
HEADERS = {"X-API-Key": API_KEY}


def client() -> TestClient:
    settings = Settings(environment="test", api_key=API_KEY, fhir_base_url="http://testserver")
    return TestClient(create_app(settings))


def test_validate_route_returns_200_for_a_valid_resource() -> None:
    with client() as api:
        response = api.post(
            "/fhir/R5/Observation/$validate",
            headers=HEADERS,
            json={
                "resourceType": "Observation",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
            },
        )
    assert response.status_code == 200
    assert response.json()["resourceType"] == "OperationOutcome"


def test_validate_route_returns_422_for_missing_required_element() -> None:
    with client() as api:
        response = api.post(
            "/fhir/R5/Condition/$validate",
            headers=HEADERS,
            json={"resourceType": "Condition"},
        )
    assert response.status_code == 422
    outcome = response.json()
    assert any(issue["severity"] == "error" for issue in outcome["issue"])


def test_validate_route_does_not_persist_the_resource() -> None:
    with client() as api:
        api.post(
            "/fhir/R5/Patient/$validate",
            headers=HEADERS,
            json={"resourceType": "Patient", "id": "should-not-be-saved"},
        )
        read = api.get("/fhir/R5/Patient/should-not-be-saved", headers=HEADERS)
    assert read.status_code == 404


def test_validate_route_requires_authentication() -> None:
    with client() as api:
        response = api.post(
            "/fhir/R5/Patient/$validate",
            json={"resourceType": "Patient"},
        )
    assert response.status_code == 401


def test_validate_route_is_recorded_in_audit() -> None:
    with client() as api:
        api.post(
            "/fhir/R5/Patient/$validate",
            headers=HEADERS,
            json={"resourceType": "Patient"},
        )
        audit = api.get("/api/v1/audit", headers=HEADERS)
    actions = [entry["action"] for entry in audit.json()["entries"]]
    assert "fhir.validate" in actions
