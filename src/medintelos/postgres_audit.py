"""Postgres-backed, durable, tamper-evident audit chain.

Same hash-chaining contract as `audit.py`'s in-memory `AuditChain` (they
share `compute_entry_hash`), but survives a restart and is visible across
every process talking to the same database — which is also exactly why
concurrent appends need explicit serialization: two processes racing to
append would otherwise both read the same "last hash" and produce two
entries claiming the same `previous_hash`, silently forking the chain.

Serialization uses a Postgres advisory lock scoped to a single global chain
(`pg_advisory_xact_lock`, released automatically at transaction end). This
is deliberately simple for 0.4.0: one chain per database. Sharding the audit
log (e.g. per tenant) is not yet supported — see docs/ROADMAP.md.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from medintelos.audit import GENESIS_HASH, AuditEntry, compute_entry_hash, hmac_compare

_SCHEMA_TABLE = "audit_entries"
# Arbitrary fixed key identifying "the audit chain" for pg_advisory_xact_lock.
# A single constant is correct as long as there is exactly one chain per
# database, which matches this module's documented 0.4.0 scope.
_ADVISORY_LOCK_KEY = 725_017_001


class PostgresAuditChain:
    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 5) -> None:
        self._pool = ConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    def close(self) -> None:
        self._pool.close()

    def append(
        self,
        *,
        actor: str,
        action: str,
        resource: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry_metadata = metadata or {}
        with self._pool.connection() as conn:
            with conn.transaction():
                conn.execute("SELECT pg_advisory_xact_lock(%s)", (_ADVISORY_LOCK_KEY,))

                last = conn.execute(
                    f"SELECT entry_hash FROM {_SCHEMA_TABLE} ORDER BY id DESC LIMIT 1"
                ).fetchone()
                previous_hash = cast(dict[str, Any], last)["entry_hash"] if last else GENESIS_HASH

                entry_id = str(uuid4())
                timestamp = datetime.now(timezone.utc).isoformat()
                digest = compute_entry_hash(
                    entry_id=entry_id,
                    timestamp=timestamp,
                    actor=actor,
                    action=action,
                    resource=resource,
                    metadata=entry_metadata,
                    previous_hash=previous_hash,
                )

                conn.execute(
                    f"""
                    INSERT INTO {_SCHEMA_TABLE}
                        (entry_id, "timestamp", actor, action, resource,
                         metadata, previous_hash, entry_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        entry_id,
                        timestamp,
                        actor,
                        action,
                        resource,
                        json.dumps(entry_metadata),
                        previous_hash,
                        digest,
                    ),
                )

        return AuditEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            actor=actor,
            action=action,
            resource=resource,
            metadata=entry_metadata,
            previous_hash=previous_hash,
            entry_hash=digest,
        )

    def list_entries(self) -> list[dict[str, Any]]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT entry_id, "timestamp", actor, action, resource,
                       metadata, previous_hash, entry_hash
                FROM {_SCHEMA_TABLE}
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def verify(self) -> bool:
        previous_hash = GENESIS_HASH
        for row in self.list_entries():
            digest = compute_entry_hash(
                entry_id=row["entry_id"],
                timestamp=row["timestamp"],
                actor=row["actor"],
                action=row["action"],
                resource=row["resource"],
                metadata=row["metadata"],
                previous_hash=row["previous_hash"],
            )
            if row["previous_hash"] != previous_hash:
                return False
            if not hmac_compare(digest, row["entry_hash"]):
                return False
            previous_hash = row["entry_hash"]
        return True
