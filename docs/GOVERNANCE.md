# Governance

This document covers process decisions that live in GitHub repository
settings rather than in tracked files, plus the versioning and release rules
that keep `CHANGELOG.md` and `docs/ROADMAP.md` meaningful.

## Branch protection (apply in GitHub → Settings → Branches → `main`)

- [ ] Require a pull request before merging (no direct pushes to `main`)
- [ ] Require status checks to pass before merging:
  - `python (3.11)`
  - `python (3.12)`
  - `contracts`
- [ ] Require branches to be up to date before merging
- [ ] Require review from Code Owners (`.github/CODEOWNERS`) — becomes
      meaningful once a second maintainer with write access exists; until
      then this only self-documents intent
- [ ] Dismiss stale reviews when new commits are pushed
- [ ] Do not allow force pushes to `main`
- [ ] Do not allow deletion of `main`

These cannot be set from a commit; a repository admin must apply them once.

## Versioning

MedIntelOS follows semantic versioning against the `medintelos` Python
package and the deployed contract interfaces independently:

- **Patch** (`0.1.x`): bug fixes, documentation, CI changes, no behavior
  change to any public API, FHIR route, CDSS output, or contract interface.
- **Minor** (`0.x.0`): additive changes — new endpoints, new CDSS rules with
  a published source, new contract functions — without breaking existing
  callers.
- **Major** (`x.0.0`): breaking changes to the API surface, FHIR resource
  handling, or contract interface. Contract interface breaks require a new
  deployment; they cannot be pushed to an existing address.

Every release updates `CHANGELOG.md` under a dated version heading before the
tag is created — not after.

## Release process

1. Confirm every checkbox for the target milestone in `docs/ROADMAP.md` is
   closed.
2. Update `CHANGELOG.md`.
3. Bump `version` in `pyproject.toml` and `package.json` together.
4. Tag the release only after CI is green on `main` at the tagged commit.
5. If the release includes a contract change, confirm
   `docs/CONTRACT_AUDIT_CHECKLIST.md` status explicitly in the release notes
   — "unchanged," "testnet only," or "audited," never silent.

## Clinical and security review

- Any change touching `src/medintelos/cdss.py` follows the "Clinical Changes"
  section of `CONTRIBUTING.md` and requires a reviewer able to assess
  clinical and human-factors impact, per `README.md`'s Contributing section.
- Any change touching `src/medintelos/security.py`, `contracts/`, or
  `contract-tests/` should get a second pair of eyes even while the project
  has a single maintainer — request review from an external contributor
  before merging when at all possible.
