\# Changelog



All notable changes will be documented here.



\## Unreleased (targeting 0.2.0 — Governance and CI hardening)



\- Fixed `mypy` configuration: `python\_version = "3.11"` made mypy crash

&#x20; immediately against current `numpy` type stubs, so the check documented in

&#x20; `CONTRIBUTING.md` and `docs/VALIDATION.md` was not actually running.

&#x20; `python\_version` is now `3.12`.

\- Added `mypy src/medintelos` as a required step in `.github/workflows/ci.yml`

&#x20; (previously only `ruff check .` and `pytest` were enforced).

\- Added `.github/CODEOWNERS` for clinical, security, and contract-adjacent

&#x20; paths.

\- Added `.github/ISSUE\_TEMPLATE/feature\_request.yml`.

\- Added `docs/ROADMAP.md` with dependency-ordered milestones through 1.0.0.

\- Added `docs/GOVERNANCE.md` (branch protection, versioning, release process).

\- Added `docs/CONTRACT\_AUDIT\_CHECKLIST.md` gating any non-testnet deployment

&#x20; of the consent/audit contracts on an external audit.



\## \[0.1.0-alpha] - 2026-09-03



\*\*First tagged release of MedIntelOS: `v0.1.0-alpha`.\*\*



The changes below were implemented and merged prior to this date; the tag

itself (commit `4e86bce`) was created on 2026-09-03 — that is the release's

actual date of record, not the date the underlying work was completed.



\- Added installable Python package and FastAPI application.

\- Added FHIR R5 JSON builders and an in-memory CRUD/search reference store.

\- Added CDS Hooks discovery, patient-view evaluation, and validated request models.

\- Added testable federated update providers and fixed first-round aggregation.

\- Added tamper-evident in-memory audit records.

\- Restricted proxy consent to patient-authorized proxies in the Solidity contract.

\- Added Docker, CI, Python tests, contract tests, and technical documentation.

\- Replaced unsupported production and compliance claims with explicit boundaries.

\- Added `CITATION.cff` for academic citation (ORCID: 0009-0006-1340-0232).

