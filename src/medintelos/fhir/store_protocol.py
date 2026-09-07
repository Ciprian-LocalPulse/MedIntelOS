"""Structural interface implemented by every FHIR store backend.

`fhir/repository.py` (in-memory) and `fhir/postgres_repository.py` (Postgres)
both satisfy this protocol without inheriting from a common base class. This
keeps the in-memory store free of any dependency on the Postgres driver, and
lets `create_app()` type-hint `app.state.fhir_store` against one interface
regardless of which backend `MEDINTELOS_FHIR_BACKEND` selects.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FHIRStoreProtocol(Protocol):
    def create(self, resource_type: str, resource: dict[str, Any]) -> dict[str, Any]: ...

    def read(self, resource_type: str, resource_id: str) -> dict[str, Any]: ...

    def update(
        self,
        resource_type: str,
        resource_id: str,
        resource: dict[str, Any],
        expected_version: str | None = None,
    ) -> dict[str, Any]: ...

    def delete(self, resource_type: str, resource_id: str) -> None: ...

    def search(self, resource_type: str, parameters: dict[str, str]) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...
