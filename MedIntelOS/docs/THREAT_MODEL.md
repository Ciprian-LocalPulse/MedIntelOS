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
| Unauthorized API access | Constant-time API-key comparison | OIDC, scopes, MFA where appropriate, rotation, rate limits |
| Resource overwrite | `If-Match` version checks | Durable transactions, authorization, history, backups |
| Sensitive logging | Audit stores action metadata only | Log review, redaction tests, SIEM access policy |
| Malicious model update | Shape checks and basic norm outlier detection | Signatures, attestation, robust aggregation, quarantine |
| Privacy leakage from models | Optional clipping/noise experiment | Formal accountant, sampling proof, privacy review |
| Smart-contract privilege abuse | Owner checks and explicit proxy authorization | Multisig, timelocks, monitoring, independent audit |
| On-chain privacy leakage | Documentation prohibits PHI | Data classification, linkage analysis, retention design |
| Clinical automation bias | Explicit warnings and deterministic explanations | Human-factors testing, governance, monitoring, override review |
| Denial of service | Body-size limit and bounded API request lists | Gateway limits, queues, autoscaling, circuit breakers |

## Non-Goals

The repository does not defend against a compromised host, malicious maintainer,
stolen deployment keys, supply-chain compromise, traffic analysis, a dishonest
majority of federated participants, or coercion of blockchain participants.

## Review Checklist

Before any deployment, document data flows, lawful basis, retention, tenant
boundaries, emergency access, key custody, dependency provenance, incident
response, disaster recovery, clinical ownership, and rollback authority.
