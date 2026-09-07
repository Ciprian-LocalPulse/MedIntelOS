# Changelog

All notable changes will be documented here.

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
