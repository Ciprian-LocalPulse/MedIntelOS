"""Thread-safe in-memory FHIR resource repository."""

from __future__ import annotations

import re
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

FHIR_ID = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")


class FHIRStoreError(ValueError):
    pass


class ResourceNotFound(FHIRStoreError):
    pass


class VersionConflict(FHIRStoreError):
    pass


class FHIRStore:
    """Development repository implementing a useful subset of FHIR REST semantics."""

    def __init__(self) -> None:
        self._resources: dict[str, dict[str, dict[str, Any]]] = {}
        self._lock = threading.RLock()

    def create(self, resource_type: str, resource: dict[str, Any]) -> dict[str, Any]:
        self._validate(resource_type, resource)
        with self._lock:
            stored = deepcopy(resource)
            resource_id = stored.get("id") or str(uuid4())
            if not FHIR_ID.fullmatch(resource_id):
                raise FHIRStoreError("Invalid FHIR resource id")
            bucket = self._resources.setdefault(resource_type, {})
            if resource_id in bucket:
                raise VersionConflict(f"{resource_type}/{resource_id} already exists")
            stored["id"] = resource_id
            stored["meta"] = self._next_meta(stored.get("meta"), 1)
            bucket[resource_id] = stored
            return deepcopy(stored)

    def read(self, resource_type: str, resource_id: str) -> dict[str, Any]:
        with self._lock:
            try:
                return deepcopy(self._resources[resource_type][resource_id])
            except KeyError as exc:
                raise ResourceNotFound(f"{resource_type}/{resource_id} not found") from exc

    def update(
        self,
        resource_type: str,
        resource_id: str,
        resource: dict[str, Any],
        expected_version: str | None = None,
    ) -> dict[str, Any]:
        self._validate(resource_type, resource)
        with self._lock:
            current = self.read(resource_type, resource_id)
            current_version = current.get("meta", {}).get("versionId", "1")
            if expected_version is not None and expected_version != current_version:
                raise VersionConflict("FHIR version conflict")
            stored = deepcopy(resource)
            stored["id"] = resource_id
            stored["meta"] = self._next_meta(
                stored.get("meta"), int(current_version) + 1
            )
            self._resources[resource_type][resource_id] = stored
            return deepcopy(stored)

    def delete(self, resource_type: str, resource_id: str) -> None:
        with self._lock:
            if resource_id not in self._resources.get(resource_type, {}):
                raise ResourceNotFound(f"{resource_type}/{resource_id} not found")
            del self._resources[resource_type][resource_id]

    def search(self, resource_type: str, parameters: dict[str, str]) -> list[dict[str, Any]]:
        with self._lock:
            resources = [deepcopy(item) for item in self._resources.get(resource_type, {}).values()]
        for name, value in parameters.items():
            if name.startswith("_"):
                continue
            resources = [item for item in resources if self._matches(item, name, value)]
        return resources

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
        updated = deepcopy(meta) if meta else {}
        updated["versionId"] = str(version)
        updated["lastUpdated"] = datetime.now(timezone.utc).isoformat()
        return updated
