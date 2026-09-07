# Changelog

All notable changes will be documented here.

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
