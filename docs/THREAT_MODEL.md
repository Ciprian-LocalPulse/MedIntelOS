# Threat Model

## Assets

- Patient and clinician identity bindings
- FHIR resources and access tokens
- Clinical rule configuration and outputs
- Model weights, updates, metrics, and participant metadata
- Consent state, institution approvals, and contract administration keys
- Audit integrity and availability

## Trust Boundaries

The HTTP client, API process, FHIR persistence layer, federated participant,
aggregation service, blockchain node, wallet, and observability pipeline are
separate trust domains. Do not infer trust from network location alone.

## Principal Threats

| Threat | Reference mitigation | Required deployment work |
|---|---|---|
| Unauthorized API access | Constant-time API-key comparison; optional OIDC bearer-token auth with SMART-style scopes (0.4.0) | MFA at the identity provider where appropriate, key/token rotation, a real IdP in front of MEDINTELOS_OAUTH_JWKS_URL |
| Excessive/abusive request volume | Per-client token-bucket rate limiting (0.4.0), in-memory per process | Shared (multi-instance) limiter before running more than one API process; gateway-level limits as defense in depth |
| Resource overwrite | `If-Match` version checks | Durable transactions, authorization, history, backups |
| Sensitive logging | Audit stores action metadata only | Log review, redaction tests, SIEM access policy |
| Malicious model update | Shape checks and basic norm outlier detection | Signatures, attestation, robust aggregation, quarantine |
| Privacy leakage from models | Optional clipping/noise experiment | Formal accountant, sampling proof, privacy review |
| Smart-contract privilege abuse | Owner checks and explicit proxy authorization | Multisig, timelocks, monitoring, independent audit |
| On-chain privacy leakage | Documentation prohibits PHI | Data classification, linkage analysis, retention design |
| Clinical automation bias | Explicit warnings and deterministic explanations | Human-factors testing, governance, monitoring, override review |
| Denial of service | Body-size limit, bounded API request lists, per-client rate limiting | Gateway limits, queues, autoscaling, circuit breakers |
| Audit chain forgery/loss | Hash-chained entries; Postgres backend serializes appends via advisory lock so concurrent writers can't fork the chain (0.4.0) | Independent anchoring (e.g. periodic external timestamping), WORM storage, backup of the audit database itself |
| Bulk export job access | System-level `$export` restricted to full-access credentials; job ids are unguessable UUIDs (0.5.0) | Per-principal job ownership checks (any authenticated caller who has a job id can currently poll/download it — see `fhir/bulk_export.py`), durable job storage instead of in-process memory |

## Non-Goals

The repository does not defend against a compromised host, malicious maintainer,
stolen deployment keys, supply-chain compromise, traffic analysis, a dishonest
majority of federated participants, or coercion of blockchain participants.

## Review Checklist

Before any deployment, document data flows, lawful basis, retention, tenant
boundaries, emergency access, key custody, dependency provenance, incident
response, disaster recovery, clinical ownership, and rollback authority.
