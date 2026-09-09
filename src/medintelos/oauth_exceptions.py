"""OAuth types with no dependency on httpx/jwt.

Split out from oauth.py so that api/auth.py — imported unconditionally by
app.py, unlike oauth.py itself — doesn't force the `oauth` extra's
dependencies onto every install. See app.py's `_build_fhir_store` /
`create_app` for the same lazy-import pattern applied to the postgres
extra.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class OAuthError(Exception):
    """Raised for any bearer-token validation failure. Mapped to HTTP 401."""


@dataclass(frozen=True)
class OAuthPrincipal:
    subject: str
    scopes: frozenset[str]
    claims: dict[str, Any]
    # SMART launch-context claims, when present. Neither is required by
    # OAuth/OIDC itself — they're SMART App Launch conventions carried in
    # the access token by an authorization server that supports launch
    # context. None when the token doesn't carry them (e.g. a
    # client-credentials/system token with no launch context).
    fhir_user: str | None = None
    launch_patient: str | None = None
