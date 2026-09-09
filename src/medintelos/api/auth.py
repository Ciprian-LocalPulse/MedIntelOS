"""Combined authentication (API key + OAuth2/OIDC) and SMART-style scope
enforcement for FHIR routes.

Design choice, stated plainly: an API-key client is treated as a trusted
system-level integration (full access, scope checks bypassed), matching how
it already behaved before OAuth existed. An OAuth client is treated as a
scoped user/patient-level client whose `scope` claim is enforced per route.
This mirrors the common real-world split between a backend service
credential and a SMART app's user-consented scopes — it is a simplification,
not a full SMART App Launch implementation (that's 0.5.0; see
docs/ROADMAP.md).
"""

from __future__ import annotations

import hmac
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Depends, Header, HTTPException, status

from medintelos.config import Settings
from medintelos.oauth_exceptions import OAuthError

if TYPE_CHECKING:
    from medintelos.oauth import OIDCAuthenticator


@dataclass(frozen=True)
class AuthContext:
    actor: str
    auth_method: str  # "api-key" | "oauth" | "disabled"
    scopes: frozenset[str]
    full_access: bool
    # SMART launch-context, oauth-only; both None for api-key/disabled auth.
    # See patient_compartment_permits() for how launch_patient is enforced.
    fhir_user: str | None = None
    launch_patient: str | None = None

    def __str__(self) -> str:
        # AuditChain.append(actor=...) expects a string; passing an
        # AuthContext directly works because of this.
        return self.actor


_SMART_ACTIONS = {"read", "write"}


def scope_permits(scopes: frozenset[str], resource_type: str, action: str) -> bool:
    """SMART v1-style scope check: `<compartment>/<resource>.<action>`.

    Accepts `*` for the resource, and `*` for the action, per the SMART
    spec's shorthand (e.g. `patient/*.read`, `user/Observation.*`). A
    `write` scope also satisfies a `read` check, matching SMART semantics
    (write implies read). The compartment (`patient`/`user`/`system`) is
    accepted but not yet distinguished — see docs/ROADMAP.md 0.5.0 for
    compartment-aware enforcement.
    """
    if action not in _SMART_ACTIONS:
        raise ValueError(f"Unknown action {action!r}")
    for scope in scopes:
        compartment_and_rest = scope.split("/", 1)
        if len(compartment_and_rest) != 2:
            continue
        _compartment, rest = compartment_and_rest
        res, _, scope_action = rest.partition(".")
        if res not in {"*", resource_type}:
            continue
        if scope_action in {"*", action}:
            return True
        if scope_action == "write" and action == "read":
            return True
    return False


class CombinedAuthenticator:
    """FastAPI dependency accepting either `X-API-Key` or `Authorization: Bearer`.

    API-key is checked first (cheap, no network/JWKS involved) so existing
    API-key-only deployments pay no extra cost. If OAuth is disabled in
    settings, an Authorization header is simply not accepted.
    """

    def __init__(self, settings: Settings, oidc: OIDCAuthenticator | None = None) -> None:
        self.settings = settings
        self._oidc = oidc

    async def __call__(
        self,
        x_api_key: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ) -> AuthContext:
        if not self.settings.require_api_key and not self.settings.oauth_enabled:
            return AuthContext(
                actor="authentication-disabled",
                auth_method="disabled",
                scopes=frozenset(),
                full_access=True,
            )

        if x_api_key is not None:
            if hmac.compare_digest(x_api_key, self.settings.api_key):
                return AuthContext(
                    actor="api-key-client",
                    auth_method="api-key",
                    scopes=frozenset(),
                    full_access=True,
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if authorization is not None and self.settings.oauth_enabled and self._oidc is not None:
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header must be 'Bearer <token>'",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            try:
                principal = self._oidc.authenticate(token)
            except OAuthError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(exc),
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
            return AuthContext(
                actor=f"oauth:{principal.subject}",
                auth_method="oauth",
                scopes=principal.scopes,
                full_access=False,
                fhir_user=principal.fhir_user,
                launch_patient=principal.launch_patient,
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
            headers={"WWW-Authenticate": "ApiKey, Bearer"},
        )


def require_fhir_scope(
    authenticate: Callable[..., Awaitable[AuthContext]], action: str
) -> Callable[..., Awaitable[AuthContext]]:
    """Build a per-route dependency enforcing a SMART scope on top of `authenticate`.

    `resource_type` is taken from the route's own path parameter — FastAPI
    injects it automatically because the parameter name here matches the
    path template (e.g. `/fhir/R5/{resource_type}`). API-key clients
    (`full_access=True`) skip the scope check entirely; see the module
    docstring for why.
    """

    async def dependency(
        resource_type: str, auth: AuthContext = Depends(authenticate)
    ) -> AuthContext:
        if not auth.full_access and not scope_permits(auth.scopes, resource_type, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient scope for {action} on {resource_type}. "
                    f"Have: {sorted(auth.scopes)}"
                ),
            )
        return auth

    return dependency


def patient_compartment_permits(
    auth: AuthContext, resource_type: str, resource: dict[str, object]
) -> bool:
    """Restricts access to the patient named by a SMART launch context.

    Only applies when `auth.launch_patient` is set (an OAuth token that
    carried a `patient` launch-context claim); every other auth path is
    unaffected — this never restricts an API-key client or a
    non-launch-context OAuth client.

    **Boundary, stated plainly:** enforced on read and search only (see
    api/app.py). Create/update/delete do not yet check the launch patient
    against the resource being written — a launch-scoped client could still
    write data for a different patient. Closing that gap is tracked in
    docs/ROADMAP.md. This is also not the full FHIR "Patient Compartment"
    definition (which includes indirect relationships like a Practitioner's
    other patients); it only checks a direct `subject` reference or the
    Patient resource's own id.
    """
    if auth.launch_patient is None:
        return True
    if resource_type == "Patient":
        return resource.get("id") == auth.launch_patient
    subject = resource.get("subject")
    if isinstance(subject, dict):
        reference = subject.get("reference")
        return reference in {auth.launch_patient, f"Patient/{auth.launch_patient}"}
    # Resource type has no subject linkage MedIntelOS understands (e.g. it
    # isn't Observation/Condition/MedicationRequest) — no compartment
    # concept applies, so don't restrict it.
    return True


__all__ = [
    "AuthContext",
    "CombinedAuthenticator",
    "patient_compartment_permits",
    "require_fhir_scope",
    "scope_permits",
]
