# Architecture

## Design Goals

MedIntelOS separates interoperability, decision-support, model coordination,
audit, and consent concerns so each can be tested or replaced independently.
The reference implementation favors explicit boundaries over hidden integration.

## Runtime Components

### API Boundary

`medintelos.api.app` owns HTTP validation, authentication, body-size limits,
security headers, error mapping, and audit events. FastAPI generates OpenAPI
documentation from the same Pydantic schemas used at runtime.

### FHIR Reference Repository

`FHIRStore` keeps deep-copied JSON resources in process memory. It checks that
the URL type matches `resourceType`, assigns IDs, increments `meta.versionId`,
supports weak ETags through `If-Match`, and implements a narrow exact-match
search subset. It is intentionally replaceable with a real FHIR repository.

### Clinical Decision Support

The CDSS layer accepts a normalized `PatientContext`, computes deterministic
rule outputs, creates alerts, and serializes alerts as CDS Hooks cards. Clinical
logic has no direct database or network dependency. That makes threshold tests
possible, but does not constitute clinical validation.

### Federated Coordinator

The coordinator manages participant metadata and round state. A deployment
injects an `update_provider` callback to obtain local updates. Aggregation checks
layer names, shapes, sample counts, and round identity before weighted averaging.
The included Gaussian-noise mechanism is an experiment, not a complete DP system.

### Audit

Each in-memory audit entry includes the previous entry hash. This detects local
mutation when the whole chain is verified. A production implementation needs an
append-only durable sink, access controls, retention policy, clock strategy,
external anchoring, monitoring, and tested recovery.

### Consent Contracts

Contracts track institution verification, patient grants, patient-authorized
proxies, revocation, time bounds, emergency references, and audit events. Legal
identity, capacity, guardianship, purpose enforcement, and off-chain deletion are
outside Ethereum and must be implemented by governance and application layers.

## Data Rules

- Use only synthetic data in this repository and its CI.
- Never place PHI or raw clinical payloads in contract state or events.
- Treat model updates as potentially sensitive and malicious.
- Keep audit metadata minimal and exclude request bodies.
- Use opaque identifiers when integrating with external systems.

## Production Replacement Points

| Reference component | Expected production replacement |
|---|---|
| Static API key | OIDC/OAuth 2.0 authorization server and policy engine |
| `FHIRStore` | Conformance-tested persistent FHIR repository |
| In-memory audit chain | Durable append-only audit service and SIEM pipeline |
| Update callback | Mutually authenticated transport and job protocol |
| Basic outlier detector | Vetted robust aggregation and adversarial controls |
| Demo drug sets | Licensed, maintained, versioned medication knowledge base |
| Direct contract owner | Reviewed multisig or governance process |
