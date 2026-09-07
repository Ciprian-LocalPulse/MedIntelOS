# Deployment Guide

## Local Evaluation

Use synthetic data only. Set a new API key and run `docker compose up --build`.
The container runs without root privileges, drops Linux capabilities, uses a
read-only root filesystem, and exposes port 8080.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `MEDINTELOS_APP_NAME` | Service name | `MedIntelOS` |
| `MEDINTELOS_ENVIRONMENT` | Runtime environment | `development` |
| `MEDINTELOS_API_KEY` | Reference API credential | Unsafe development value |
| `MEDINTELOS_FHIR_BASE_URL` | URLs advertised in metadata | `http://localhost:8080` |
| `MEDINTELOS_REQUIRE_API_KEY` | Enable API-key boundary | `true` |
| `MEDINTELOS_MAX_RESOURCE_BYTES` | HTTP body limit | `1000000` |

Production mode refuses the built-in API key and requires at least 24 characters.
This length check is only a configuration guard, not a credential-management
solution.

## Production Readiness Gate

Do not expose the reference container to patient data. A production program must
replace volatile storage, add TLS and an identity provider, enforce authorization
per resource and purpose, validate FHIR profiles and terminology, encrypt durable
data, isolate tenants, implement backups, monitor security events, and complete
clinical and regulatory validation.

## Contract Deployment

Use a development chain first. Pin compiler and dependency hashes, run static
analysis, commission an independent audit, define upgrade and pause strategy,
use a multisig administrator, test key loss, and review all events for privacy.

The contract records erasure evidence; it cannot erase off-chain replicas or
immutable blockchain history. Do not market that event as proof of legal erasure.

### Deployment sequence (with governance)

`MedIntelOSGovernance` (see [contracts/MedIntelOSGovernance.sol](../contracts/MedIntelOSGovernance.sol))
implements the "multisig administrator" referenced above as an N-of-M
propose/approve/execute contract with a mandatory timelock delay. It replaces
a single EOA as `owner` on both contracts below.

1. Deploy `MedIntelOSGovernance` with the initial signer set, approval
   threshold, and timelock delay (seconds). Choose these values deliberately —
   changing them later itself requires a governance proposal.
2. Deploy `MedIntelOSAuditLedger` with the zero address.
3. Deploy `MedIntelOSConsentManager` with the ledger address.
4. Call `setConsentManager` on the ledger (from the deployer EOA — this still
   happens before ownership handoff).
5. Transfer administrative control: from the deployer EOA, call
   `transferOwnership(governanceAddress)` on both `MedIntelOSAuditLedger` and
   `MedIntelOSConsentManager`. From this point on, every `onlyOwner` function
   on either contract can only be reached by a governance proposal that
   clears signer threshold and the timelock delay — there is no remaining
   single-signature path. Verify `owner()` on both contracts equals the
   governance address before proceeding, and treat the deployer key as
   retired for admin purposes afterward.
6. Register and independently verify institution identities — `verifyInstitution`
   now requires a governance proposal to reach threshold + timelock before it
   executes, rather than a single signature.
7. Commission the external audit in `docs/CONTRACT_AUDIT_CHECKLIST.md` — of
   the consent/audit contracts **and** of `MedIntelOSGovernance` — before any
   non-testnet deployment. None of the steps above substitute for that audit.

Identity binding for governance signers (who they are, how their keys are
custodied, how a lost key is replaced) is an off-chain, operator-defined
process — see [docs/DID_VC_DESIGN.md](DID_VC_DESIGN.md) for the related,
separate design covering patient/institution identity linkage.
