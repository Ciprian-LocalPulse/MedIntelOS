# Changelog

All notable changes will be documented here.

## Unreleased (targeting 0.5.0 — FHIR interoperability depth)

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
  OAuth tokens into `AuthContext`.
- Added patient-compartment enforcement (`patient_compartment_permits`) on
  FHIR read and search when a token carries a launch-context patient.
  Documented boundary: not yet enforced on create/update/delete.
- Added Bulk Data `$export` (system- and type-level kick-off, status
  polling, NDJSON download, cancellation) modeled on HL7's Bulk Data Access
  pattern. Runs synchronously in-process — see `fhir/bulk_export.py`'s
  documented non-durable, single-process boundary. System-level export is
  restricted to full-access (API-key) callers.

## Unreleased (targeting 0.4.0 — Production-grade authentication)

- Added OAuth2/OIDC bearer-token authentication (`oauth.py`,
  `api/auth.py`'s `CombinedAuthenticator`), alongside the existing API-key
  path. Disabled by default (`MEDINTELOS_OAUTH_ENABLED=false`).
- Added SMART v1-style scope enforcement on FHIR routes
  (`require_fhir_scope`, `scope_permits`). API-key clients remain full-access
  (system-level), matching prior behavior; OAuth clients are scope-limited.
- Added in-memory token-bucket rate limiting (`rate_limit.py`), enabled by
  default, with a `Retry-After` header on `429`. `/health` is exempt.
- Added `PostgresAuditChain`, a durable, hash-chain-compatible audit backend
  selected via `MEDINTELOS_AUDIT_BACKEND=postgres`, serialized across
  processes with a Postgres advisory lock. Extracted the hashing logic
  (`compute_entry_hash`) so both audit backends produce identical hashes for
  identical inputs.
- Added migration `0002_audit_entries.py`.
- Marked `security.py`'s `APIKeyAuthenticator` as superseded by
  `CombinedAuthenticator` (kept for backward compatibility; logic unchanged).

## Unreleased (targeting 0.3.0 — Persistent FHIR store)

- Added `PostgresFHIRStore`, a drop-in Postgres-backed implementation of the
  FHIR store interface, selected via `MEDINTELOS_FHIR_BACKEND=postgres`. The
  in-memory store remains the default and is unaffected.
- Added Alembic migrations (`migrations/`), starting with the
  `fhir_resources` table.
- Added `docker-compose.postgres.yml`, an opt-in override adding a `db`
  service and a one-shot `migrate` service; the default `docker-compose.yml`
  is unchanged.
- Added `tests/test_postgres_fhir.py`, run in CI against a real Postgres
  service container; skipped locally unless `MEDINTELOS_TEST_DATABASE_URL`
  is set.
- Fixed: FHIR store calls in `api/app.py` were synchronous and blocking
  inside `async def` route handlers. Harmless with the in-memory backend,
  but would have blocked the event loop under real load once backed by
  network I/O. Now wrapped in `run_in_threadpool`.
- Fixed: replaced the deprecated `@app.on_event("shutdown")` with FastAPI's
  `lifespan` context manager, which now also closes the Postgres connection
  pool cleanly on shutdown.
- Documented backup/restore and migration workflow in `docs/DEPLOYMENT.md`.

## Unreleased (targeting 0.2.0 — Governance and CI hardening)

- Fixed `mypy` configuration: `python_version = "3.11"` made mypy crash
  immediately against current `numpy` type stubs, so the check documented in
  `CONTRIBUTING.md` and `docs/VALIDATION.md` was not actually running.
  `python_version` is now `3.12`.
- Added `mypy src/medintelos` as a required step in `.github/workflows/ci.yml`
  (previously only `ruff check .` and `pytest` were enforced).
- Added `.github/CODEOWNERS` for clinical, security, and contract-adjacent
  paths.
- Added `.github/ISSUE_TEMPLATE/feature_request.yml`.
- Added `docs/ROADMAP.md` with dependency-ordered milestones through 1.0.0.
- Added `docs/GOVERNANCE.md` (branch protection, versioning, release process).
- Added `docs/CONTRACT_AUDIT_CHECKLIST.md` gating any non-testnet deployment
  of the consent/audit contracts on an external audit.

## 0.1.0 - 2026-06-14

- Added installable Python package and FastAPI application.
- Added FHIR R5 JSON builders and an in-memory CRUD/search reference store.
- Added CDS Hooks discovery, patient-view evaluation, and validated request models.
- Added testable federated update providers and fixed first-round aggregation.
- Added tamper-evident in-memory audit records.
- Restricted proxy consent to patient-authorized proxies in the Solidity contract.
- Added Docker, CI, Python tests, contract tests, and technical documentation.
- Replaced unsupported production and compliance claims with explicit boundaries.
