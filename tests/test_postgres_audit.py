"""Integration tests for PostgresAuditChain.

Requires a real Postgres reachable at MEDINTELOS_TEST_DATABASE_URL with
migrations applied (`alembic upgrade head`) — see tests/test_postgres_fhir.py
for the identical skip pattern and rationale.
"""

from __future__ import annotations

import os
import threading

import psycopg
import pytest

from medintelos.postgres_audit import PostgresAuditChain

DATABASE_URL = os.getenv("MEDINTELOS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="MEDINTELOS_TEST_DATABASE_URL not set; skipping Postgres integration tests",
)


@pytest.fixture
def chain():
    assert DATABASE_URL is not None
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE TABLE audit_entries RESTART IDENTITY")
    backend = PostgresAuditChain(DATABASE_URL)
    yield backend
    backend.close()


def test_append_returns_linked_entry(chain):
    first = chain.append(actor="tester", action="fhir.read", resource="Patient/1")
    second = chain.append(actor="tester", action="fhir.read", resource="Patient/2")
    assert second.previous_hash == first.entry_hash


def test_verify_true_for_untampered_chain(chain):
    for i in range(5):
        chain.append(actor="tester", action="fhir.read", resource=f"Patient/{i}")
    assert chain.verify() is True


def test_verify_false_after_direct_tampering(chain):
    entry = chain.append(actor="tester", action="fhir.read", resource="Patient/1")
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:  # type: ignore[arg-type]
        conn.execute(
            "UPDATE audit_entries SET actor = 'attacker' WHERE entry_id = %s",
            (entry.entry_id,),
        )
    assert chain.verify() is False


def test_chain_survives_a_new_instance(chain):
    chain.append(actor="tester", action="fhir.read", resource="Patient/1")
    second_handle = PostgresAuditChain(DATABASE_URL)  # type: ignore[arg-type]
    try:
        entries = second_handle.list_entries()
    finally:
        second_handle.close()
    assert len(entries) == 1


def test_concurrent_appends_produce_a_single_valid_chain(chain):
    """The whole reason for the advisory lock in postgres_audit.py: without
    it, two processes racing to append could both read the same "last hash"
    and insert two entries claiming the same previous_hash, forking the
    chain. 20 threads x 5 appends each is enough to reliably trigger the
    race if the lock were missing or broken.
    """
    errors: list[Exception] = []

    def worker(n: int) -> None:
        try:
            for i in range(5):
                chain.append(actor=f"worker-{n}", action="fhir.read", resource=f"Patient/{n}-{i}")
        except Exception as exc:  # pragma: no cover - only on real failure
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(chain.list_entries()) == 100
    assert chain.verify() is True
