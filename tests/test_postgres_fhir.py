"""Integration tests for PostgresFHIRStore.

Requires a real Postgres reachable at MEDINTELOS_TEST_DATABASE_URL, with
migrations already applied (`alembic upgrade head`). Skipped entirely
otherwise, so contributors who never touch the Postgres backend don't need
Postgres installed to run `pytest`. CI provides a Postgres service container
for this — see .github/workflows/ci.yml.

Each test truncates the table first so tests don't depend on run order or
leak state between runs.
"""

from __future__ import annotations

import os

import psycopg
import pytest

from medintelos.fhir.exceptions import ResourceNotFound, VersionConflict
from medintelos.fhir.postgres_repository import PostgresFHIRStore

DATABASE_URL = os.getenv("MEDINTELOS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="MEDINTELOS_TEST_DATABASE_URL not set; skipping Postgres integration tests",
)


@pytest.fixture
def store():
    assert DATABASE_URL is not None
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE TABLE fhir_resources")
    backend = PostgresFHIRStore(DATABASE_URL)
    yield backend
    backend.close()


def _patient(patient_id: str | None = None) -> dict:
    resource = {"resourceType": "Patient", "name": [{"family": "Doe"}]}
    if patient_id:
        resource["id"] = patient_id
    return resource


def test_create_assigns_id_and_version(store):
    created = store.create("Patient", _patient())
    assert created["id"]
    assert created["meta"]["versionId"] == "1"


def test_create_rejects_duplicate_id(store):
    store.create("Patient", _patient("dup-1"))
    with pytest.raises(VersionConflict):
        store.create("Patient", _patient("dup-1"))


def test_read_round_trips_document(store):
    created = store.create("Patient", _patient("read-1"))
    fetched = store.read("Patient", "read-1")
    assert fetched == created


def test_read_missing_raises_not_found(store):
    with pytest.raises(ResourceNotFound):
        store.read("Patient", "does-not-exist")


def test_update_increments_version(store):
    store.create("Patient", _patient("upd-1"))
    updated = store.update("Patient", "upd-1", _patient("upd-1"))
    assert updated["meta"]["versionId"] == "2"


def test_update_rejects_stale_version(store):
    store.create("Patient", _patient("upd-2"))
    with pytest.raises(VersionConflict):
        store.update("Patient", "upd-2", _patient("upd-2"), expected_version="99")


def test_update_missing_raises_not_found(store):
    with pytest.raises(ResourceNotFound):
        store.update("Patient", "missing", _patient("missing"))


def test_delete_removes_resource(store):
    store.create("Patient", _patient("del-1"))
    store.delete("Patient", "del-1")
    with pytest.raises(ResourceNotFound):
        store.read("Patient", "del-1")


def test_delete_missing_raises_not_found(store):
    with pytest.raises(ResourceNotFound):
        store.delete("Patient", "does-not-exist")


def test_search_filters_by_subject_reference(store):
    match = {
        "resourceType": "Observation",
        "id": "obs-1",
        "subject": {"reference": "Patient/search-1"},
    }
    other = {
        "resourceType": "Observation",
        "id": "obs-2",
        "subject": {"reference": "Patient/search-2"},
    }
    store.create("Observation", match)
    store.create("Observation", other)

    results = store.search("Observation", {"patient": "search-1"})

    assert [item["id"] for item in results] == ["obs-1"]


def test_data_survives_a_new_store_instance(store):
    """The whole point of 0.3.0: unlike FHIRStore, this must not be in-memory."""
    store.create("Patient", _patient("persist-1"))
    second_handle = PostgresFHIRStore(DATABASE_URL)
    try:
        fetched = second_handle.read("Patient", "persist-1")
    finally:
        second_handle.close()
    assert fetched["id"] == "persist-1"
