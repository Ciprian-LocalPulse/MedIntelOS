from fastapi.testclient import TestClient

from medintelos.api.app import create_app
from medintelos.config import Settings

API_KEY = "test-key-with-sufficient-length"


def test_smart_configuration_404_when_oauth_disabled():
    settings = Settings(environment="test", api_key=API_KEY, fhir_base_url="http://testserver")
    with TestClient(create_app(settings)) as api:
        response = api.get("/fhir/R5/.well-known/smart-configuration")
    assert response.status_code == 404


def test_smart_configuration_when_oauth_enabled():
    settings = Settings(
        environment="test",
        api_key=API_KEY,
        fhir_base_url="http://testserver",
        oauth_enabled=True,
        oauth_issuer="https://issuer.example.test",
        oauth_audience="medintelos-api",
        oauth_jwks_url="https://issuer.example.test/jwks.json",
        oauth_authorization_endpoint="https://issuer.example.test/authorize",
        oauth_token_endpoint="https://issuer.example.test/token",
    )
    with TestClient(create_app(settings)) as api:
        response = api.get("/fhir/R5/.well-known/smart-configuration")
    assert response.status_code == 200
    document = response.json()
    assert document["issuer"] == "https://issuer.example.test"
    assert document["authorization_endpoint"] == "https://issuer.example.test/authorize"
    assert document["token_endpoint"] == "https://issuer.example.test/token"
    assert "launch/patient" in document["scopes_supported"]
    assert "code_challenge_methods_supported" in document


def test_smart_configuration_omits_unset_endpoints():
    settings = Settings(
        environment="test",
        api_key=API_KEY,
        fhir_base_url="http://testserver",
        oauth_enabled=True,
        oauth_issuer="https://issuer.example.test",
        oauth_audience="medintelos-api",
        oauth_jwks_url="https://issuer.example.test/jwks.json",
    )
    with TestClient(create_app(settings)) as api:
        response = api.get("/fhir/R5/.well-known/smart-configuration")
    document = response.json()
    assert "authorization_endpoint" not in document
    assert "token_endpoint" not in document


def test_capability_statement_has_no_oauth_extension_when_disabled():
    settings = Settings(environment="test", api_key=API_KEY, fhir_base_url="http://testserver")
    with TestClient(create_app(settings)) as api:
        response = api.get("/fhir/R5/metadata", headers={"X-API-Key": API_KEY})
    security = response.json()["rest"][0]["security"]
    assert "extension" not in security


def test_capability_statement_advertises_oauth_uris_when_enabled():
    settings = Settings(
        environment="test",
        api_key=API_KEY,
        fhir_base_url="http://testserver",
        oauth_enabled=True,
        oauth_issuer="https://issuer.example.test",
        oauth_audience="medintelos-api",
        oauth_jwks_url="https://issuer.example.test/jwks.json",
        oauth_authorization_endpoint="https://issuer.example.test/authorize",
        oauth_token_endpoint="https://issuer.example.test/token",
    )
    with TestClient(create_app(settings)) as api:
        response = api.get("/fhir/R5/metadata", headers={"X-API-Key": API_KEY})
    security = response.json()["rest"][0]["security"]
    extension = security["extension"][0]
    assert extension["url"] == "http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris"
    sub_extensions = {ext["url"]: ext["valueUri"] for ext in extension["extension"]}
    assert sub_extensions["authorize"] == "https://issuer.example.test/authorize"
    assert sub_extensions["token"] == "https://issuer.example.test/token"


def test_metadata_route_does_not_require_write_scope():
    # /fhir/R5/metadata has no auth dependency at all in app.py — confirm it
    # stays reachable without credentials, matching normal FHIR server
    # behavior (CapabilityStatement is meant to be publicly discoverable).
    settings = Settings(environment="test", api_key=API_KEY, fhir_base_url="http://testserver")
    with TestClient(create_app(settings)) as api:
        response = api.get("/fhir/R5/metadata")
    assert response.status_code == 200
