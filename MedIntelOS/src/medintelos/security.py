"""Small authentication boundary for the reference API."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from medintelos.config import Settings


class APIKeyAuthenticator:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def __call__(self, x_api_key: str | None = Header(default=None)) -> str:
        if not self.settings.require_api_key:
            return "authentication-disabled"
        if x_api_key is None or not hmac.compare_digest(x_api_key, self.settings.api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        return "api-key-client"
