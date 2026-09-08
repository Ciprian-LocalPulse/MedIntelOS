"""Tamper-evident, in-memory audit chain for development and tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class AuditEntry:
    entry_id: str
    timestamp: str
    actor: str
    action: str
    resource: str
    metadata: dict[str, Any]
    previous_hash: str
    entry_hash: str


GENESIS_HASH = "0" * 64


def compute_entry_hash(
    *,
    entry_id: str,
    timestamp: str,
    actor: str,
    action: str,
    resource: str,
    metadata: dict[str, Any],
    previous_hash: str,
) -> str:
    """Pure hashing function shared by every audit chain backend.

    Kept separate from any storage concern so `audit.py` (in-memory) and
    `postgres_audit.py` produce byte-identical hashes for the same inputs —
    a chain started on one backend and inspected via the other (e.g. during
    a migration) verifies consistently.
    """
    payload = {
        "entry_id": entry_id,
        "timestamp": timestamp,
        "actor": actor,
        "action": action,
        "resource": resource,
        "metadata": metadata,
        "previous_hash": previous_hash,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class AuditChain:
    """Append-only hash chain, held in process memory.

    Selected via `MEDINTELOS_AUDIT_BACKEND=memory` (the default). For
    anything that must survive a restart, use `PostgresAuditChain` in
    postgres_audit.py instead — see docs/DEPLOYMENT.md.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = threading.RLock()

    def close(self) -> None:
        """No-op: satisfies the same interface as PostgresAuditChain."""

    def append(
        self,
        *,
        actor: str,
        action: str,
        resource: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        with self._lock:
            previous_hash = self._entries[-1].entry_hash if self._entries else GENESIS_HASH
            entry_id = str(uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            entry_metadata = metadata or {}
            digest = compute_entry_hash(
                entry_id=entry_id,
                timestamp=timestamp,
                actor=actor,
                action=action,
                resource=resource,
                metadata=entry_metadata,
                previous_hash=previous_hash,
            )
            entry = AuditEntry(
                entry_id=entry_id,
                timestamp=timestamp,
                actor=actor,
                action=action,
                resource=resource,
                metadata=entry_metadata,
                previous_hash=previous_hash,
                entry_hash=digest,
            )
            self._entries.append(entry)
            return entry

    def list_entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return [asdict(entry) for entry in self._entries]

    def verify(self) -> bool:
        with self._lock:
            previous_hash = GENESIS_HASH
            for entry in self._entries:
                digest = compute_entry_hash(
                    entry_id=entry.entry_id,
                    timestamp=entry.timestamp,
                    actor=entry.actor,
                    action=entry.action,
                    resource=entry.resource,
                    metadata=entry.metadata,
                    previous_hash=entry.previous_hash,
                )
                if entry.previous_hash != previous_hash:
                    return False
                if not hmac_compare(digest, entry.entry_hash):
                    return False
                previous_hash = entry.entry_hash
            return True


def hmac_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
