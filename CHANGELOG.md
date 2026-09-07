\# Changelog



All notable changes will be documented here.



\## Unreleased (targeting 0.8.0 — Consent contract audit and governance)



\- Added `contracts/MedIntelOSGovernance.sol`: an N-of-M multisig with a

&#x20; mandatory timelock delay (propose / approve / execute / cancel),

&#x20; intended to hold `owner` on `MedIntelOSConsentManager` and

&#x20; `MedIntelOSAuditLedger` instead of a single EOA.

\- Added `transferOwnership` to `MedIntelOSConsentManager` and

&#x20; `MedIntelOSAuditLedger` so ownership can be handed to the new governance

&#x20; contract post-deployment.

\- Added `contract-tests/governance.ts` covering threshold gating, timelock

&#x20; gating, duplicate-approval idempotency, approval revocation, self-gated

&#x20; admin functions, proposal cancellation, and an end-to-end ownership

&#x20; transfer + governance-executed `verifyInstitution` call.

\- Added `docs/DID_VC_DESIGN.md`: a design-only document for linking

&#x20; wallet-based patient/institution identity to a DID/Verifiable Credential,

&#x20; kept entirely off-chain. Not implemented.

\- Updated `docs/DEPLOYMENT.md` with a governance-aware contract deployment

&#x20; sequence.

\- Updated `docs/ROADMAP.md` 0.8.0 status. The external audit item for both

&#x20; contracts remains open and unchecked — it requires an independent

&#x20; third-party auditor and is not satisfied by this change.



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

