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


class AuditChain:
    """Append-only hash chain. Replace with durable storage in real deployments."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = threading.RLock()

    def append(
        self,
        *,
        actor: str,
        action: str,
        resource: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        with self._lock:
            previous_hash = self._entries[-1].entry_hash if self._entries else "0" * 64
            entry_id = str(uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            entry_metadata = metadata or {}
            payload = {
                "entry_id": entry_id,
                "timestamp": timestamp,
                "actor": actor,
                "action": action,
                "resource": resource,
                "metadata": entry_metadata,
                "previous_hash": previous_hash,
            }
            digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
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
            previous_hash = "0" * 64
            for entry in self._entries:
                payload = asdict(entry)
                entry_hash = payload.pop("entry_hash")
                if payload["previous_hash"] != previous_hash:
                    return False
                digest = hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                if not hmac_compare(digest, entry_hash):
                    return False
                previous_hash = entry_hash
            return True


def hmac_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
