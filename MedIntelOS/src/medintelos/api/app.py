"""FastAPI application exposing the reference MedIntelOS services."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse

from medintelos.api.schemas import CDSHooksRequest, CDSSRequest, PatientContextRequest
from medintelos.audit import AuditChain
from medintelos.cdss import (
    CDSHookType,
    CDSSEngine,
    LabResult,
    PatientContext,
    VitalSigns,
)
from medintelos.config import Settings
from medintelos.fhir.builders import BundleType, FHIRBundleBuilder, build_capability_statement
from medintelos.fhir.repository import (
    FHIRStore,
    FHIRStoreError,
    ResourceNotFound,
    VersionConflict,
)
from medintelos.security import APIKeyAuthenticator


def operation_outcome(message: str, code: str = "processing") -> dict[str, Any]:
    return {
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "error", "code": code, "diagnostics": message}],
    }


def _to_domain(request: PatientContextRequest) -> PatientContext:
    data = request.model_dump()
    vitals_data = data.pop("vitals")
    labs_data = data.pop("labs")
    return PatientContext(
        **data,
        vitals=VitalSigns(**vitals_data) if vitals_data else None,
        labs=[LabResult(**item) for item in labs_data],
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()

    app = FastAPI(
        title="MedIntelOS Reference API",
        version="0.1.0",
        description=(
            "Educational reference implementation for FHIR R5 resource handling, "
            "CDS Hooks integration, and clinical decision-support experiments. "
            "Not validated for patient care."
        ),
        license_info={"name": "MIT", "identifier": "MIT"},
    )
    app.state.settings = settings
    app.state.fhir_store = FHIRStore()
    app.state.audit = AuditChain()
    app.state.cdss = CDSSEngine()
    authenticate = APIKeyAuthenticator(settings)

    @app.middleware("http")
    async def reject_oversized_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_resource_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content=operation_outcome("Request body exceeds configured limit", "too-costly"),
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ResourceNotFound)
    async def not_found_handler(_: Request, exc: ResourceNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content=operation_outcome(str(exc), "not-found"))

    @app.exception_handler(VersionConflict)
    async def conflict_handler(_: Request, exc: VersionConflict) -> JSONResponse:
        return JSONResponse(status_code=409, content=operation_outcome(str(exc), "conflict"))

    @app.exception_handler(FHIRStoreError)
    async def fhir_error_handler(_: Request, exc: FHIRStoreError) -> JSONResponse:
        return JSONResponse(status_code=400, content=operation_outcome(str(exc), "invalid"))

    @app.get("/health", tags=["Operations"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name, "environment": settings.environment}

    @app.get("/cds-services", tags=["CDS Hooks"])
    async def cds_discovery() -> dict[str, Any]:
        return {
            "services": [
                {
                    "hook": "patient-view",
                    "title": "MedIntelOS patient review",
                    "description": "Evaluates an explicitly supplied, synthetic-safe patient context.",
                    "id": "medintelos-patient-view",
                    "prefetch": {"medintelosContext": "Patient/{{context.patientId}}/$medintelos-context"},
                    "usageRequirements": "Research and evaluation only; not validated for clinical care.",
                }
            ]
        }

    @app.post("/api/v1/cdss/evaluate", tags=["Clinical decision support"])
    async def evaluate_cdss(
        payload: CDSSRequest,
        actor: str = Depends(authenticate),
    ) -> dict[str, Any]:
        result = app.state.cdss.evaluate(_to_domain(payload.context), CDSHookType(payload.hook))
        app.state.audit.append(
            actor=actor,
            action="cdss.evaluate",
            resource=f"Patient/{payload.context.patient_id}",
            metadata={"hook": payload.hook, "card_count": len(result["cards"])},
        )
        return result

    @app.post("/cds-services/medintelos-patient-view", tags=["CDS Hooks"])
    async def cds_hook(
        payload: CDSHooksRequest,
        actor: str = Depends(authenticate),
    ) -> dict[str, Any]:
        context_data = payload.prefetch.get("medintelosContext")
        if not isinstance(context_data, dict):
            raise HTTPException(
                status_code=422,
                detail="prefetch.medintelosContext must contain a MedIntelOS patient context",
            )
        context = PatientContextRequest.model_validate(context_data)
        result = app.state.cdss.evaluate(_to_domain(context), CDSHookType.PATIENT_VIEW)
        app.state.audit.append(
            actor=actor,
            action="cds-hooks.patient-view",
            resource=f"Patient/{context.patient_id}",
            metadata={"hook_instance": payload.hookInstance, "card_count": len(result["cards"])},
        )
        return result

    @app.get("/fhir/R5/metadata", tags=["FHIR R5"])
    async def metadata() -> dict[str, Any]:
        return build_capability_statement(settings.fhir_base_url)

    @app.post("/fhir/R5/{resource_type}", status_code=201, tags=["FHIR R5"])
    async def create_resource(
        resource_type: str,
        resource: dict[str, Any],
        response: Response,
        actor: str = Depends(authenticate),
    ) -> dict[str, Any]:
        created = app.state.fhir_store.create(resource_type, resource)
        location = f"/fhir/R5/{resource_type}/{created['id']}"
        response.headers["Location"] = location
        response.headers["ETag"] = f"W/\"{created['meta']['versionId']}\""
        app.state.audit.append(actor=actor, action="fhir.create", resource=location)
        return created

    @app.get("/fhir/R5/{resource_type}/{resource_id}", tags=["FHIR R5"])
    async def read_resource(
        resource_type: str,
        resource_id: str,
        response: Response,
        actor: str = Depends(authenticate),
    ) -> dict[str, Any]:
        resource = app.state.fhir_store.read(resource_type, resource_id)
        response.headers["ETag"] = f"W/\"{resource['meta']['versionId']}\""
        app.state.audit.append(
            actor=actor,
            action="fhir.read",
            resource=f"{resource_type}/{resource_id}",
        )
        return resource

    @app.get("/fhir/R5/{resource_type}", tags=["FHIR R5"])
    async def search_resources(
        request: Request,
        resource_type: str,
        count: int = Query(default=50, alias="_count", ge=1, le=200),
        actor: str = Depends(authenticate),
    ) -> dict[str, Any]:
        params = {
            key: value
            for key, value in request.query_params.items()
            if key != "_count"
        }
        matches = app.state.fhir_store.search(resource_type, params)[:count]
        app.state.audit.append(
            actor=actor,
            action="fhir.search",
            resource=resource_type,
            metadata={"result_count": len(matches), "parameter_names": sorted(params)},
        )
        builder = FHIRBundleBuilder(BundleType.SEARCHSET)
        for match in matches:
            builder.add_resource(match)
        return builder.build_searchset(
            search_url=f"{settings.fhir_base_url}/fhir/R5/{resource_type}",
            total=len(matches),
        )

    @app.put("/fhir/R5/{resource_type}/{resource_id}", tags=["FHIR R5"])
    async def update_resource(
        resource_type: str,
        resource_id: str,
        resource: dict[str, Any],
        response: Response,
        request: Request,
        actor: str = Depends(authenticate),
    ) -> dict[str, Any]:
        if_match = request.headers.get("if-match")
        expected_version = if_match.replace('W/"', "").replace('"', "") if if_match else None
        updated = app.state.fhir_store.update(
            resource_type, resource_id, resource, expected_version=expected_version
        )
        response.headers["ETag"] = f"W/\"{updated['meta']['versionId']}\""
        app.state.audit.append(
            actor=actor,
            action="fhir.update",
            resource=f"{resource_type}/{resource_id}",
        )
        return updated

    @app.delete(
        "/fhir/R5/{resource_type}/{resource_id}",
        status_code=204,
        tags=["FHIR R5"],
    )
    async def delete_resource(
        resource_type: str,
        resource_id: str,
        actor: str = Depends(authenticate),
    ) -> Response:
        app.state.fhir_store.delete(resource_type, resource_id)
        app.state.audit.append(
            actor=actor,
            action="fhir.delete",
            resource=f"{resource_type}/{resource_id}",
        )
        return Response(status_code=204)

    @app.get("/api/v1/audit", tags=["Audit"])
    async def audit_entries(actor: str = Depends(authenticate)) -> dict[str, Any]:
        entries = app.state.audit.list_entries()
        return {"chain_valid": app.state.audit.verify(), "entries": entries, "requested_by": actor}

    return app


app = create_app()
