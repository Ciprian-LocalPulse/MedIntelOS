# Changelog

All notable changes will be documented here.

## [0.6.0] - 2026-09-10

This release bundles milestones 0.2.0 through 0.6.0 from `docs/ROADMAP.md`,
merged incrementally into `main` as separate PRs and released together here.

### CDSS evidence and conformance (0.6.0)

- **Fixed two real clinical scoring defects**, found while verifying every
  citation and threshold in `cdss.py` against their published sources
  (not just adding citations to already-correct code):
  - **NEWS2 heart rate 41-50 bpm was scoring 1 point instead of 2** per the
    published Royal College of Physicians chart — under-scoring
    bradycardia and potentially delaying escalation.
  - **AKI KDIGO's absolute creatinine ≥4.0 mg/dL (stage 3) criterion only
    fired when a baseline creatinine was also available.** A patient
    presenting with e.g. Cr 4.5 mg/dL and no known baseline — common at
    initial presentation, before any prior labs exist — was scored stage 0,
    missing severe AKI entirely.
- **Fixed a systemic truthy-check bug** in `qsofa()` and `news2()`: vitals
  were checked with `if vitals.heart_rate:` instead of
  `if vitals.heart_rate is not None:`, so a genuinely measured value of
  **0** (e.g. respiratory_rate=0/apnea, heart_rate=0/asystole — the most
  dangerous possible readings) was silently treated identically to "not
  measured" and skipped. `LabResult.is_critical`/`is_abnormal` already used
  `is not None` correctly; this brought the vital-sign checks in line with
  that existing discipline.
- Verified (via primary-source search, not from memory) every existing
  citation in `cdss.py` — qSOFA (Singer et al., JAMA 2016), NEWS2 (RCP
  2017), KDIGO AKI (2012), CHA2DS2-VASc (Lip et al., Chest 2010) including
  its published annual-stroke-risk table — against their sources. All were
  already accurate; the NEWS2 reference was expanded to the full citation.
- Documented NEWS2's SpO2 Scale 1-only boundary explicitly (Scale 2, for
  patients with a target 88-92% saturation range, is not implemented —
  `VitalSigns` has no field to indicate that clinical context).
- Corrected a stale code comment claiming `"hard-stop"` is a valid CDS
  Hooks `Card.indicator` value — it was renamed to `"critical"` in the spec
  in 2018. Actual card construction was already correct; only the comment
  was wrong.
- Added `tests/test_cdss_boundaries.py` and `tests/test_cds_hooks_conformance.py`.

### FHIR interoperability depth (0.5.0)

- **Plan revision, documented before implementation:** researched current
  publication status of US Core and IPS — neither has a FHIR R5 release
  (both are R4-based) — so profile validation was implemented as
  MedIntelOS's own honestly-scoped required-element checks against the FHIR
  R5 base spec, not a US Core/IPS conformance claim. See
  `fhir/validation.py`'s module docstring.
- Added the `$validate` operation (`POST /fhir/R5/{resourceType}/$validate`)
  returning an `OperationOutcome`; does not persist the resource.
- Added `fhir/terminology.py`: a small local LOINC table for vital signs,
  checked (as warnings, not errors) by `$validate`.
- Added `/fhir/R5/.well-known/smart-configuration` and the `oauth-uris`
  CapabilityStatement extension (SMART App Launch discovery, resource-server
  side only).
- Added `fhirUser` and launch-context `patient` claim propagation from
  OAuth tokens into `AuthContext`, plus patient-compartment enforcement on
  FHIR read and search (not yet on create/update/delete).
- Added Bulk Data `$export` (system- and type-level kick-off, status
  polling, NDJSON download, cancellation), modeled on HL7's Bulk Data
  Access pattern. Runs synchronously in-process — see
  `fhir/bulk_export.py`'s documented non-durable, single-process boundary.

### Production-grade authentication (0.4.0)

- Added OAuth2/OIDC bearer-token authentication (`oauth.py`,
  `api/auth.py`'s `CombinedAuthenticator`), alongside the existing API-key
  path. Disabled by default (`MEDINTELOS_OAUTH_ENABLED=false`).
- Added SMART v1-style scope enforcement on FHIR routes. API-key clients
  remain full-access (system-level); OAuth clients are scope-limited.
- Added in-memory token-bucket rate limiting, enabled by default, with a
  `Retry-After` header on `429`. `/health` is exempt.
- Added `PostgresAuditChain`, a durable, hash-chain-compatible audit
  backend, serialized across processes with a Postgres advisory lock.
- Marked `security.py`'s `APIKeyAuthenticator` as superseded by
  `CombinedAuthenticator` (kept for backward compatibility).

### Persistent FHIR store (0.3.0)

- Added `PostgresFHIRStore`, selected via `MEDINTELOS_FHIR_BACKEND=postgres`.
  The in-memory store remains the default.
- Added Alembic migrations, `docker-compose.postgres.yml` opt-in override.
- Fixed: FHIR store calls in `api/app.py` were synchronous/blocking inside
  `async def` route handlers; wrapped in `run_in_threadpool`.
- Fixed: replaced deprecated `@app.on_event("shutdown")` with FastAPI's
  `lifespan` context manager.

### Governance and CI hardening (0.2.0)

- Fixed `mypy` configuration: `python_version = "3.11"` made mypy crash
  immediately against current `numpy` type stubs, so the check documented in
  `CONTRIBUTING.md` and `docs/VALIDATION.md` was not actually running.
- Added `mypy src/medintelos` as a required CI step, `.github/CODEOWNERS`,
  feature-request issue template, `docs/ROADMAP.md`, `docs/GOVERNANCE.md`,
  `docs/CONTRACT_AUDIT_CHECKLIST.md`.

## 0.1.0 - 2026-06-14

- Added installable Python package and FastAPI application.
- Added FHIR R5 JSON builders and an in-memory CRUD/search reference store.
- Added CDS Hooks discovery, patient-view evaluation, and validated request models.
- Added testable federated update providers and fixed first-round aggregation.
- Added tamper-evident in-memory audit records.
- Restricted proxy consent to patient-authorized proxies in the Solidity contract.
- Added Docker, CI, Python tests, contract tests, and technical documentation.
- Replaced unsupported production and compliance claims with explicit boundaries.
