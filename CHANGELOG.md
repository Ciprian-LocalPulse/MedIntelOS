# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - targeting 0.2.0

*Governance and CI hardening*

### Fixed
- **Mypy Configuration**: Updated `python_version` from `3.11` to `3.12`. Previously, `3.11` caused `mypy` to crash immediately against current `numpy` type stubs, preventing validation checks documented in `CONTRIBUTING.md` and `docs/VALIDATION.md` from running.

### Added
- **CI Workflow**: Added `mypy src/medintelos` as a required validation step in `.github/workflows/ci.yml` (previously only `ruff check .` and `pytest` were enforced).
- **Code Ownership**: Added `.github/CODEOWNERS` for clinical, security, and smart contract paths.
- **Templates & Documentation**:
  - Added `.github/ISSUE_TEMPLATE/feature_request.yml`.
  - Added `docs/ROADMAP.md` detailing dependency-ordered milestones through version `1.0.0`.
  - Added `docs/GOVERNANCE.md` covering branch protection rules, versioning guidelines, and the release process.
  - Added `docs/CONTRACT_AUDIT_CHECKLIST.md` gating non-testnet deployment of consent and audit smart contracts on external security audits.

---

## [0.1.0-alpha] - 2026-09-03

> **First tagged release of MedIntelOS (`v0.1.0-alpha`)**
> *Release commit:* `4e86bce` (date of record: September 3, 2026).

### Added
- Installable Python package architecture and FastAPI core application.
- FHIR R5 JSON builders along with an in-memory CRUD/search reference store.
- CDS Hooks discovery mechanism, patient-view evaluation, and validated request models.
- Testable federated update providers and resolved first-round aggregation logic.
- Tamper-evident in-memory audit log records.
- Docker containerization, CI pipelines, Python test suite, contract tests, and core technical documentation.
- `CITATION.cff` file for academic citations (ORCID: `0009-0006-1340-0232`).

### Security & Compliance
- **Smart Contracts**: Restricted proxy consent strictly to patient-authorized proxies in the Solidity contract implementation.
- **Compliance Scope**: Replaced unsupported production and compliance claims with explicit system boundary definitions.
