"""Structural interface implemented by every audit chain backend.

See fhir/store_protocol.py for why this pattern is used instead of a shared
base class: it keeps the in-memory chain free of any Postgres dependency.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from medintelos.audit import AuditEntry


@runtime_checkable
class AuditChainProtocol(Protocol):
    def append(
        self,
        *,
        actor: str,
        action: str,
        resource: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry: ...

    def list_entries(self) -> list[dict[str, Any]]: ...

    def verify(self) -> bool: ...

    def close(self) -> None: ...
