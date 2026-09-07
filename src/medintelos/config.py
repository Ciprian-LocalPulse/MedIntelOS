"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


_VALID_FHIR_BACKENDS = {"memory", "postgres"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "MedIntelOS"
    environment: str = "development"
    api_key: str = "change-me-before-use"
    fhir_base_url: str = "http://localhost:8080"
    require_api_key: bool = True
    max_resource_bytes: int = 1_000_000
    fhir_backend: str = "memory"
    database_url: str | None = None
    database_pool_min_size: int = 1
    database_pool_max_size: int = 10

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("MEDINTELOS_APP_NAME", cls.app_name),
            environment=os.getenv("MEDINTELOS_ENVIRONMENT", cls.environment),
            api_key=os.getenv("MEDINTELOS_API_KEY", cls.api_key),
            fhir_base_url=os.getenv("MEDINTELOS_FHIR_BASE_URL", cls.fhir_base_url),
            require_api_key=_as_bool(os.getenv("MEDINTELOS_REQUIRE_API_KEY", "true")),
            max_resource_bytes=int(
                os.getenv("MEDINTELOS_MAX_RESOURCE_BYTES", str(cls.max_resource_bytes))
            ),
            fhir_backend=os.getenv("MEDINTELOS_FHIR_BACKEND", cls.fhir_backend),
            database_url=os.getenv("MEDINTELOS_DATABASE_URL"),
            database_pool_min_size=int(
                os.getenv("MEDINTELOS_DATABASE_POOL_MIN_SIZE", str(cls.database_pool_min_size))
            ),
            database_pool_max_size=int(
                os.getenv("MEDINTELOS_DATABASE_POOL_MAX_SIZE", str(cls.database_pool_max_size))
            ),
        )

    def validate(self) -> None:
        if self.require_api_key and self.environment == "production":
            if self.api_key == "change-me-before-use" or len(self.api_key) < 24:
                raise ValueError("Set a strong MEDINTELOS_API_KEY in production")
        if self.fhir_backend not in _VALID_FHIR_BACKENDS:
            raise ValueError(
                f"MEDINTELOS_FHIR_BACKEND must be one of {sorted(_VALID_FHIR_BACKENDS)}, "
                f"got {self.fhir_backend!r}"
            )
        if self.fhir_backend == "postgres" and not self.database_url:
            raise ValueError(
                "MEDINTELOS_DATABASE_URL is required when MEDINTELOS_FHIR_BACKEND=postgres"
            )
