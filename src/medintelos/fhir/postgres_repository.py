"""Postgres-backed FHIR resource repository.

Same interface and semantics as `fhir/repository.py`'s in-memory `FHIRStore`
(see `fhir/store_protocol.py`), backed by a single table with the current
version of each resource. This is a drop-in replacement selected by
`MEDINTELOS_FHIR_BACKEND=postgres` (see config.py and docs/DEPLOYMENT.md).

Boundary: this table stores only the *current* version of each resource, not
full version history. `_history` reads/writes, `vread`, and FHIR history
operations are out of scope for 0.3.0 — see docs/ROADMAP.md.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from medintelos.fhir.exceptions import FHIRStoreError, ResourceNotFound, VersionConflict

FHIR_ID = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")

_SCHEMA_TABLE = "fhir_resources"


class PostgresFHIRStore:
    """FHIR resource repository backed by Postgres.

    Expects the schema created by the Alembic migrations in `migrations/`.
    Does not create or migrate the schema itself — run `alembic upgrade head`
    as a separate, explicit step before starting the API against this
    backend (see docs/DEPLOYMENT.md).
    """

    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 10) -> None:
        self._pool = ConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    def close(self) -> None:
        self._pool.close()

    # -- CRUD -----------------------------------------------------------

    def create(self, resource_type: str, resource: dict[str, Any]) -> dict[str, Any]:
        self._validate(resource_type, resource)
        resource_id = resource.get("id") or str(uuid4())
        if not FHIR_ID.fullmatch(resource_id):
            raise FHIRStoreError("Invalid FHIR resource id")

        stored = dict(resource)
        stored["id"] = resource_id
        stored["meta"] = self._next_meta(stored.get("meta"), 1)

        with self._pool.connection() as conn:
            try:
                conn.execute(
                    f"""
                    INSERT INTO {_SCHEMA_TABLE}
                        (resource_type, resource_id, version_id, document, last_updated)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        resource_type,
                        resource_id,
                        1,
                        json.dumps(stored),
                        _parse_last_updated(stored["meta"]["lastUpdated"]),
                    ),
                )
            except psycopg.errors.UniqueViolation as exc:
                raise VersionConflict(f"{resource_type}/{resource_id} already exists") from exc
        return stored

    def read(self, resource_type: str, resource_id: str) -> dict[str, Any]:
        with self._pool.connection() as conn:
            row = conn.execute(
                f"""
                SELECT document FROM {_SCHEMA_TABLE}
                WHERE resource_type = %s AND resource_id = %s
                """,
                (resource_type, resource_id),
            ).fetchone()
        if row is None:
            raise ResourceNotFound(f"{resource_type}/{resource_id} not found")
        return cast(dict[str, Any], row)["document"]

    def update(
        self,
        resource_type: str,
        resource_id: str,
        resource: dict[str, Any],
        expected_version: str | None = None,
    ) -> dict[str, Any]:
        self._validate(resource_type, resource)

        with self._pool.connection() as conn:
            with conn.transaction():
                current = conn.execute(
                    f"""
                    SELECT version_id FROM {_SCHEMA_TABLE}
                    WHERE resource_type = %s AND resource_id = %s
                    FOR UPDATE
                    """,
                    (resource_type, resource_id),
                ).fetchone()
                if current is None:
                    raise ResourceNotFound(f"{resource_type}/{resource_id} not found")

                current_version = cast(dict[str, Any], current)["version_id"]
                if expected_version is not None and str(expected_version) != str(current_version):
                    raise VersionConflict("FHIR version conflict")

                stored = dict(resource)
                stored["id"] = resource_id
                stored["meta"] = self._next_meta(stored.get("meta"), current_version + 1)

                conn.execute(
                    f"""
                    UPDATE {_SCHEMA_TABLE}
                    SET version_id = %s, document = %s, last_updated = %s
                    WHERE resource_type = %s AND resource_id = %s
                    """,
                    (
                        current_version + 1,
                        json.dumps(stored),
                        _parse_last_updated(stored["meta"]["lastUpdated"]),
                        resource_type,
                        resource_id,
                    ),
                )
        return stored

    def delete(self, resource_type: str, resource_id: str) -> None:
        with self._pool.connection() as conn:
            cursor = conn.execute(
                f"""
                DELETE FROM {_SCHEMA_TABLE}
                WHERE resource_type = %s AND resource_id = %s
                """,
                (resource_type, resource_id),
            )
            if cursor.rowcount == 0:
                raise ResourceNotFound(f"{resource_type}/{resource_id} not found")

    def search(self, resource_type: str, parameters: dict[str, str]) -> list[dict[str, Any]]:
        # Boundary (documented in docs/ROADMAP.md 0.3.0): filtering happens in
        # Python after fetching every resource of the given type, matching the
        # in-memory store's behavior exactly rather than pushing predicates
        # into SQL/JSONB. Fine for reference/demo data volumes; revisit before
        # any deployment with a non-trivial number of resources per type.
        with self._pool.connection() as conn:
            rows = conn.execute(
                f"SELECT document FROM {_SCHEMA_TABLE} WHERE resource_type = %s",
                (resource_type,),
            ).fetchall()
        resources = [cast(dict[str, Any], row)["document"] for row in rows]
        for name, value in parameters.items():
            if name.startswith("_"):
                continue
            resources = [item for item in resources if self._matches(item, name, value)]
        return resources

    # -- helpers, identical semantics to fhir/repository.py --------------

    @staticmethod
    def _matches(resource: dict[str, Any], name: str, value: str) -> bool:
        if name in {"patient", "subject"}:
            reference = resource.get("subject", {}).get("reference", "")
            return reference in {value, f"Patient/{value}"}
        candidate = resource.get(name)
        if isinstance(candidate, list):
            return any(str(item) == value for item in candidate)
        return str(candidate) == value

    @staticmethod
    def _validate(resource_type: str, resource: dict[str, Any]) -> None:
        if not resource_type or not resource_type[0].isupper():
            raise FHIRStoreError("Invalid resource type")
        if resource.get("resourceType") != resource_type:
            raise FHIRStoreError("resourceType does not match the URL")

    @staticmethod
    def _next_meta(meta: dict[str, Any] | None, version: int) -> dict[str, Any]:
        updated = dict(meta) if meta else {}
        updated["versionId"] = str(version)
        updated["lastUpdated"] = datetime.now(timezone.utc).isoformat()
        return updated


def _parse_last_updated(value: str) -> datetime:
    return datetime.fromisoformat(value)
