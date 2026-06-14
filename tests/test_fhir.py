import pytest

from medintelos.fhir.builders import FHIRResourceBuilder
from medintelos.fhir.repository import FHIRStore, VersionConflict


def test_resource_lifecycle_and_patient_search() -> None:
    store = FHIRStore()
    patient = FHIRResourceBuilder.patient(
        patient_id="p1",
        family_name="Example",
        given_names=["Ada"],
        birth_date="1980-01-01",
        gender="female",
    )
    created_patient = store.create("Patient", patient)
    observation = FHIRResourceBuilder.observation(
        obs_id="o1",
        patient_id="p1",
        loinc_code="8867-4",
        display="Heart rate",
        value=72,
        unit="/min",
        category="vital-signs",
    )
    store.create("Observation", observation)

    matches = store.search("Observation", {"patient": "p1"})
    updated = store.update("Patient", "p1", created_patient, expected_version="1")

    assert len(matches) == 1
    assert updated["meta"]["versionId"] == "2"


def test_optimistic_locking_rejects_stale_update() -> None:
    store = FHIRStore()
    patient = {"resourceType": "Patient", "id": "p1", "active": True}
    store.create("Patient", patient)

    with pytest.raises(VersionConflict):
        store.update("Patient", "p1", patient, expected_version="9")
