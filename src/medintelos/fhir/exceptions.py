"""Exceptions shared by every FHIR store backend.

Extracted from repository.py so that fhir/postgres_repository.py can raise
the exact same exception types as the in-memory store without importing
repository.py (which would pull in threading-only implementation details it
does not need).
"""

from __future__ import annotations


class FHIRStoreError(ValueError):
    """Base class for FHIR store errors, mapped to HTTP 400 in the API layer."""


class ResourceNotFound(FHIRStoreError):
    """Raised when a resource_type/resource_id pair does not exist."""


class VersionConflict(FHIRStoreError):
    """Raised on optimistic-locking failure or duplicate-id creation."""
