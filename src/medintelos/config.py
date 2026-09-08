"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


_VALID_FHIR_BACKENDS = {"memory", "postgres"}
_VALID_AUDIT_BACKENDS = {"memory", "postgres"}


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
    audit_backend: str = "memory"

    # OAuth2/OIDC bearer-token authentication, alongside (not replacing) the
    # API-key path. Disabled by default so existing deployments are
    # unaffected until an operator deliberately configures an issuer.
    oauth_enabled: bool = False
    oauth_issuer: str | None = None
    oauth_audience: str | None = None
    oauth_jwks_url: str | None = None
    oauth_jwks_cache_seconds: int = 300

    # In-memory, per-process token-bucket rate limiting. Not a substitute for
    # a shared limiter (e.g. Redis-backed) across multiple instances — see
    # docs/ROADMAP.md 0.4.0 boundary.
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 120
    rate_limit_burst: int = 20

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
            audit_backend=os.getenv("MEDINTELOS_AUDIT_BACKEND", cls.audit_backend),
            oauth_enabled=_as_bool(os.getenv("MEDINTELOS_OAUTH_ENABLED", "false")),
            oauth_issuer=os.getenv("MEDINTELOS_OAUTH_ISSUER"),
            oauth_audience=os.getenv("MEDINTELOS_OAUTH_AUDIENCE"),
            oauth_jwks_url=os.getenv("MEDINTELOS_OAUTH_JWKS_URL"),
            oauth_jwks_cache_seconds=int(
                os.getenv(
                    "MEDINTELOS_OAUTH_JWKS_CACHE_SECONDS", str(cls.oauth_jwks_cache_seconds)
                )
            ),
            rate_limit_enabled=_as_bool(os.getenv("MEDINTELOS_RATE_LIMIT_ENABLED", "true")),
            rate_limit_requests_per_minute=int(
                os.getenv(
                    "MEDINTELOS_RATE_LIMIT_REQUESTS_PER_MINUTE",
                    str(cls.rate_limit_requests_per_minute),
                )
            ),
            rate_limit_burst=int(
                os.getenv("MEDINTELOS_RATE_LIMIT_BURST", str(cls.rate_limit_burst))
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
        if self.audit_backend not in _VALID_AUDIT_BACKENDS:
            raise ValueError(
                f"MEDINTELOS_AUDIT_BACKEND must be one of {sorted(_VALID_AUDIT_BACKENDS)}, "
                f"got {self.audit_backend!r}"
            )
        if self.audit_backend == "postgres" and not self.database_url:
            raise ValueError(
                "MEDINTELOS_DATABASE_URL is required when MEDINTELOS_AUDIT_BACKEND=postgres"
            )
        if self.oauth_enabled and not (self.oauth_issuer and self.oauth_audience and self.oauth_jwks_url):
            raise ValueError(
                "MEDINTELOS_OAUTH_ISSUER, MEDINTELOS_OAUTH_AUDIENCE, and "
                "MEDINTELOS_OAUTH_JWKS_URL are all required when "
                "MEDINTELOS_OAUTH_ENABLED=true"
            )
        if self.rate_limit_requests_per_minute <= 0:
            raise ValueError("MEDINTELOS_RATE_LIMIT_REQUESTS_PER_MINUTE must be positive")
        if self.rate_limit_burst <= 0:
            raise ValueError("MEDINTELOS_RATE_LIMIT_BURST must be positive")
