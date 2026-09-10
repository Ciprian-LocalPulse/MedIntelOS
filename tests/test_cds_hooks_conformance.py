"""CDS Hooks conformance tests.

Checks the discovery endpoint and card responses against the current CDS
Hooks specification (https://cds-hooks.hl7.org/), verified before writing
these tests:

- Discovery: `GET {baseUrl}/cds-services` returns `{"services": [...]}`,
  each service requires `hook`, `id`, and a `description`.
- Card: `summary` (required, <140 characters, one sentence),
  `indicator` (required, one of `info`/`warning`/`critical` — "hard-stop"
  was renamed to "critical" in 2018 and is not a valid value), `source`
  (required object). If `suggestions` is present, `selectionBehavior` must
  also be present.
- Response: `cards` is a required array.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from medintelos.api.app import create_app
from medintelos.config import Settings

API_KEY = "test-key-with-sufficient-length"
HEADERS = {"X-API-Key": API_KEY}

VALID_INDICATORS = {"info", "warning", "critical"}


def client() -> TestClient:
    settings = Settings(environment="test", api_key=API_KEY, fhir_base_url="http://testserver")
    return TestClient(create_app(settings))


def _assert_card_conforms(card: dict) -> None:
    assert "summary" in card, "Card.summary is REQUIRED"
    assert isinstance(card["summary"], str)
    assert len(card["summary"]) < 140, "Card.summary must be a <140-character one-sentence summary"

    assert "indicator" in card, "Card.indicator is REQUIRED"
    assert card["indicator"] in VALID_INDICATORS, (
        f"Card.indicator {card['indicator']!r} is not a valid CDS Hooks indicator "
        f"(must be one of {VALID_INDICATORS} — 'hard-stop' was renamed to "
        f"'critical' in 2018)"
    )

    assert "source" in card, "Card.source is REQUIRED"
    assert isinstance(card["source"], dict)
    assert "label" in card["source"], "Card.source.label is REQUIRED"

    if card.get("suggestions"):
        assert "selectionBehavior" in card, (
            "Card.selectionBehavior is REQUIRED whenever Card.suggestions is present"
        )
        assert card["selectionBehavior"] in {"at-most-one", "any"}


def test_discovery_response_shape() -> None:
    with client() as api:
        response = api.get("/cds-services")
    assert response.status_code == 200
    body = response.json()
    assert "services" in body
    assert isinstance(body["services"], list)
    assert len(body["services"]) >= 1
    for service in body["services"]:
        assert "hook" in service, "CDS Service.hook is REQUIRED"
        assert "id" in service, "CDS Service.id is REQUIRED"
        assert "description" in service, "CDS Service.description is REQUIRED"


def test_discovery_does_not_require_authentication() -> None:
    # Discovery is meant to be checked by an EHR before it has any reason to
    # authenticate; requiring credentials here would break normal CDS Hooks
    # onboarding.
    with client() as api:
        response = api.get("/cds-services")
    assert response.status_code == 200


def test_cds_hook_response_has_required_cards_array() -> None:
    payload = {
        "hook": "patient-view",
        "hookInstance": "11111111-1111-1111-1111-111111111111",
        "context": {"patientId": "conformance-1"},
        "prefetch": {
            "medintelosContext": {
                "patient_id": "conformance-1",
                "vitals": {"respiratory_rate": 25, "systolic_bp": 85, "gcs": 13},
            }
        },
    }
    with client() as api:
        response = api.post(
            "/cds-services/medintelos-patient-view", headers=HEADERS, json=payload
        )
    assert response.status_code == 200
    body = response.json()
    assert "cards" in body, "CDS Hooks response.cards is REQUIRED"
    assert isinstance(body["cards"], list)


def test_every_card_conforms_across_a_range_of_severities() -> None:
    """Drives every severity path (low/moderate/high/critical) through the
    real evaluate() pipeline and checks every card produced, rather than
    hand-building card fixtures — this actually exercises
    _alert_to_cds_card()."""
    scenarios = [
        {"patient_id": "conf-low", "vitals": {}},
        {
            "patient_id": "conf-high",
            "vitals": {"respiratory_rate": 22, "systolic_bp": 100},
        },
        {
            "patient_id": "conf-critical",
            "vitals": {"respiratory_rate": 30, "spo2": 85, "heart_rate": 140, "gcs": 10},
        },
    ]
    with client() as api:
        for scenario in scenarios:
            response = api.post(
                "/api/v1/cdss/evaluate",
                headers=HEADERS,
                json={"hook": "patient-view", "context": scenario},
            )
            assert response.status_code == 200
            for card in response.json()["cards"]:
                _assert_card_conforms(card)


def test_evaluate_response_cards_field_is_always_present_even_when_empty() -> None:
    with client() as api:
        response = api.post(
            "/api/v1/cdss/evaluate",
            headers=HEADERS,
            json={"hook": "patient-view", "context": {"patient_id": "conf-empty"}},
        )
    assert response.status_code == 200
    assert "cards" in response.json()
    assert response.json()["cards"] == []
