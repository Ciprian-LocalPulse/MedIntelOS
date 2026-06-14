# Validation Strategy

The automated suite verifies software behavior, not clinical safety.

## Automated Evidence

- Unit tests cover score thresholds, missing/zero threshold behavior, FHIR
  lifecycle and optimistic locking, aggregation math, audit chaining, and proxy
  authorization.
- API tests cover authentication, FHIR CRUD/search, audit emission, and CDSS output.
- Ruff checks common correctness and style issues.
- Mypy is available as a stricter engineering check.
- Solc compiles the contracts; Hardhat/Viem integration tests exercise consent
  lifecycle behavior in Linux CI.

## Evidence Required Before Clinical Use

Requirements traceability, hazard analysis, clinical association, analytical and
clinical validation, representative datasets, subgroup analysis, calibration,
human-factors studies, cybersecurity testing, data-governance review, change
control, post-market monitoring, and jurisdiction-specific regulatory review are
all outside this repository.
