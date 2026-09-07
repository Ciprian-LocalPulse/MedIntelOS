# Roadmap

MedIntelOS is at 0.1.0 (Alpha). This roadmap sequences the work needed to move
from a reference/educational implementation toward a system that could
plausibly sit behind a real integration, without ever overstating clinical or
regulatory readiness before that evidence actually exists.

Each milestone lists what ships and what it deliberately does not claim.
Nothing here is a committed date; it is a dependency-ordered plan.

## 0.2.0 — Governance and CI hardening (this milestone)

- [x] Restore and complete `.github/` automation (CI, issue templates, dependabot)
- [x] Fix `mypy` configuration (`python_version` mismatch prevented it from
      running at all against current `numpy` type stubs)
- [x] Add `mypy` as a required, non-optional CI step
- [x] Add `CODEOWNERS` for clinical, security, and contract-adjacent code
- [x] Add `docs/CONTRACT_AUDIT_CHECKLIST.md`
- [x] Add `docs/GOVERNANCE.md` (branch protection, review, release process)
- [ ] Enable branch protection on `main` per `docs/GOVERNANCE.md` (repo admin
      action, cannot be done from a file change)
- [ ] Open tracking issues for every unchecked item below, labeled by
      milestone, so the project has public, individually reviewable units of
      work instead of one large roadmap document

## 0.3.0 — Persistent FHIR store

- [ ] Postgres-backed implementation of the `FHIRStore` interface (interface
      unchanged; in-memory store remains available for tests and quick starts)
- [ ] Alembic migrations
- [ ] `docker-compose.yml` gains a `postgres` service
- [ ] Backup/restore documented in `docs/DEPLOYMENT.md`
- **Boundary:** still not a conformance-tested FHIR server; still no
  multi-tenant isolation.

## 0.4.0 — Production-grade authentication

- [ ] OAuth2/OIDC support alongside the existing API-key path (API key remains
      for local development only, gated by `environment != "production"`)
- [ ] SMART-on-FHIR-style scopes on API routes
- [ ] Rate limiting middleware
- [ ] Durable audit log (Postgres-backed, building on 0.3.0)
- **Boundary:** still no tenant isolation, still no KMS-backed secrets by
  default (documented as an operator responsibility).

## 0.5.0 — FHIR interoperability depth

- [ ] Profile validation against one named base (US Core or IPS — decided
      before work starts, tracked in an issue)
- [ ] Minimal terminology binding for codes already used by CDSS rules
- [ ] SMART App Launch
- [ ] `$export` (Bulk Data) for the resource types already supported
- **Boundary:** not a full terminology server; not FHIR-certified.

## 0.6.0 — CDSS evidence and conformance

- [ ] Primary source citation attached to every rule in `cdss.py`
  (already required for new rules by `CONTRIBUTING.md`; this milestone
  back-fills the existing ones)
- [ ] Boundary-value tests for every threshold, including missing-data paths
- [ ] CDS Hooks conformance test suite
- **Boundary:** clinical validation (analytical + clinical), human-factors
  studies, and regulatory review remain outside this repository, as stated in
  `docs/VALIDATION.md`.

## 0.7.0 — Federated learning hardening

- [ ] Formal differential-privacy accountant (e.g. via an existing DP library)
      replacing the current noise experiment
- [ ] mTLS between coordinator and participants
- [ ] Standardized model serialization (ONNX) instead of ad-hoc weight dicts
- **Boundary:** still no cryptographic secure aggregation; still assumes an
  honest majority of participants (see `docs/THREAT_MODEL.md` non-goals).

## 0.8.0 — Consent contract audit and governance

- [ ] External audit of `contracts/MedIntelOSConsent.sol` before any
      non-testnet deployment
- [ ] Multisig + timelock for administrative functions
- [ ] Documented DID/VC design for identity-to-consent linkage, kept off-chain
- **Boundary:** on-chain data remains free of PHI and direct identifiers by
  policy, not by cryptographic guarantee.

## 0.9.0 — Observability and operations

- [ ] Structured logging, Prometheus metrics, OpenTelemetry tracing
- [ ] Incident response and disaster recovery runbooks in `docs/DEPLOYMENT.md`

## 1.0.0 — Only after every "Boundary" line above is either closed or
explicitly re-documented as a deployment responsibility

1.0.0 is a statement about engineering completeness of the reference
implementation, not a clinical or regulatory claim. `MEDICAL_DISCLAIMER.md`
continues to apply at every version.

## How this roadmap is used

- Every checkbox should have a corresponding GitHub issue before work starts.
- A milestone ships when its checkboxes are closed and `CHANGELOG.md` is
  updated — not before.
- Scope moves between milestones only via an issue discussion, not silently.
