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

- [x] Postgres-backed implementation of the `FHIRStore` interface (interface
      unchanged; in-memory store remains available for tests and quick starts)
- [x] Alembic migrations
- [x] `docker-compose.yml` gains a `postgres` service (as an opt-in override,
      `docker-compose.postgres.yml`, so the default memory-backend workflow
      is unaffected)
- [x] Backup/restore documented in `docs/DEPLOYMENT.md`
- **Boundary:** still not a conformance-tested FHIR server; still no
  multi-tenant isolation.

## 0.4.0 — Production-grade authentication

- [x] OAuth2/OIDC support alongside the existing API-key path (API key remains
      for local development only, gated by `environment != "production"`)
- [x] SMART-on-FHIR-style scopes on API routes (compartment accepted but not
      yet distinguished — every compartment behaves the same; tightening
      this is part of 0.5.0's SMART App Launch work)
- [x] Rate limiting middleware (in-memory/per-process; a shared limiter is
      needed before running multiple instances — see docs/DEPLOYMENT.md)
- [x] Durable audit log (Postgres-backed, building on 0.3.0)
- **Boundary:** still no tenant isolation, still no KMS-backed secrets by
  default (documented as an operator responsibility).

## 0.5.0 — FHIR interoperability depth

- [x] Profile validation — **revised from the original plan.** Neither US
      Core nor the International Patient Summary (IPS) has a published FHIR
      R5 version as of this milestone (both are R4-based); adapting their R4
      profiles to R5 resources would have produced validation that looked
      authoritative but wasn't. Implemented instead: MedIntelOS's own
      required-element checks straight from the FHIR R5 base specification,
      exposed via the `$validate` operation (`fhir/validation.py`) —
      explicitly documented as not a conformance claim against any external
      IG. Revisit once US Core or IPS publish an R5 release.
- [x] Minimal terminology binding for codes already used by CDSS rules
      (`fhir/terminology.py` — vital-signs LOINC codes, checked as
      warnings via `$validate`, not hard errors)
- [x] SMART App Launch — resource-server side only: `.well-known/smart-configuration`
      discovery document, `oauth-uris` CapabilityStatement extension,
      `fhirUser`/launch-context `patient` claim propagation, and
      patient-compartment enforcement on read/search (not yet on
      create/update/delete — see `api/auth.py`'s `patient_compartment_permits`
      docstring). The authorization-code flow itself is the identity
      provider's responsibility, not this resource server's.
- [x] `$export` (Bulk Data) — kick-off/poll/download pattern modeled on
      HL7's Bulk Data Access IG, for the resource types already supported.
      Runs synchronously in-process (`fhir/bulk_export.py`'s documented
      boundary: not durable, not shared across instances, not sized for
      large datasets — real async job processing is future work).
- **Boundary:** not a terminology server; not FHIR-certified; `$export`
  jobs are in-memory and single-process.

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
