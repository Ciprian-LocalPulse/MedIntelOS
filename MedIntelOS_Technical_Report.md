_MedIntelOS — Technical Report_ 

# **MedIntelOS** 

A Reference Architecture for Interoperable, Explainable, and Federated Clinical Software Systems 

_An Academic System Analysis of FHIR R5 Interoperability, Clinical Decision Support, Federated Learning, Tamper-Evident Audit, and Blockchain-Mediated Consent_ 

Repository: github.com/Ciprian-LocalPulse/MedIntelOS 

License: MIT  |  Status: Alpha, Educational Reference Implementation Technical Report 

Page 1 of 34 

_MedIntelOS — Technical Report_ 

## **Abstract** 

MedIntelOS is an open-source, educational reference implementation that explores how five traditionally separate concerns in digital health engineering — standards-based interoperability, clinical decision support, privacy-preserving multi-institution machine learning, tamper-evident provenance, and patientmediated consent — can be composed into a single, modular codebase without collapsing their trust boundaries into one another. The system exposes a FHIR Release 5 (R5) resource surface backed by an inmemory, optimistic-concurrency repository; a CDS Hooks-shaped clinical decision support engine implementing published, deterministic scoring rules (qSOFA, NEWS2, a KDIGO-derived acute kidney injury rule, and CHA₂DS₂-VASc); a federated learning coordinator that performs sample-weighted aggregation with an optional Gaussian differential-privacy mechanism; a SHA-256 hash-chained audit log; and a pair of Solidity smart contracts that encode granular, purpose-based, revocable patient consent. This report presents a structured academic analysis of the repository as it exists in source form: its architecture, module boundaries, data flow, algorithmic content, security posture, and stated limitations. Ten original diagrams — rendered from the Mermaid diagramming language and grounded directly in the project's own module structure, request handlers, and contract functions — are used throughout to make the system's control flow and trust boundaries legible at a glance. Consistent with the maintainers' own documentation, this report treats MedIntelOS as what it explicitly claims to be: a rigorously honest, nonclinical, non-production teaching artifact whose primary value lies in demonstrating how interoperability, explainability, privacy engineering, provenance, and consent can be reasoned about jointly, rather than in providing a deployable clinical product. 

Page 2 of 34 

_MedIntelOS — Technical Report_ 

## **Table of Contents** 

|1. Introducton and Motvaton.....................................................................................................................|
|---|
|2. Standards and Research Context..............................................................................................................|
|3. System Architecture Overview..................................................................................................................|
|4. The FHIR R5 Interoperability Layer............................................................................................................|
|5. The Clinical Decision Support Subsystem..................................................................................................|
|6. The Federated Learning Subsystem..........................................................................................................|
|7. The Tamper-Evident Audit Layer...............................................................................................................|
|8. Blockchain-Mediated Consent Management............................................................................................|
|9. Security Architecture and Threat Model...................................................................................................|
|10. Deployment, Operatons, and Confguraton..........................................................................................|
|11. Validaton Strategy and Evidentary Gaps...............................................................................................|
|12. Limitatons, Ethics, and Future Work......................................................................................................|
|13. Conclusion...............................................................................................................................................|
|References.....................................................................................................................................................|



Page 3 of 34 

_MedIntelOS — Technical Report_ 

## **1. Introduction and Motivation** 

Digital health systems are usually built as a set of point solutions: an electronic health record (EHR) integration layer, a clinical alerting module, a research-data pipeline, an audit subsystem, and a consentmanagement process, each developed by a different team against a different set of assumptions about trust, data residency, and failure modes. The seams between these subsystems are where a large share of real-world harm originates — stale consent state feeding a research extract, an alerting rule silently changing behavior without an audit trail, or a federated model update that cannot be distinguished from an adversarial one. MedIntelOS is structured as a direct response to that observation: rather than optimizing any one subsystem in isolation, it treats interoperability, decision support, federated computation, provenance, and consent as five faces of a single design problem, and asks what a codebase looks like when the boundaries between them are made explicit, typed, and independently testable. 

The repository is unusually candid about its own maturity. Its README states plainly that it is an “alpha, educational system, not a production EHR, not a complete FHIR implementation, not a medical device, and not evidence of regulatory compliance.” This report takes that framing seriously. Rather than evaluating MedIntelOS as a candidate for clinical deployment — a category error the maintainers themselves warn against — it evaluates the project as a piece of systems-engineering scholarship: a worked example of how to decompose a multi-stakeholder health-data platform into components whose guarantees can be reasoned about individually, and whose composition risk is documented rather than hidden. 

### **1.1 Scope of This Report** 

This report analyzes the MedIntelOS repository as retrieved from source, covering the Python service layer (‘src/medintelos’), the Solidity consent and audit contracts (‘contracts/’), the accompanying documentation set (‘docs/’), and the operational tooling (Docker, Compose, and CI configuration). It is organized around the six functional pillars the maintainers themselves identify in the project's implemented-scope table, plus dedicated treatment of security posture, deployment practice, and validation methodology. Table 1 summarizes these pillars and the boundary the maintainers place around each one. 

|**Pillar**|**What is implemented**|**Explicit boundary**|
|---|---|---|
|FHIR R5|JSON resource builders, in-memory CRUD, a narrow<br>search subset, version IDs, ETags, a<br>CapabilityStatement endpoint|Not a conformance-tested or<br>persistent FHIR server|
|CDS Hooks / CDSS|Discovery endpoint and a patent-view service;<br>qSOFA, NEWS2, an AKI rule, and a CHA₂DS₂-VASc<br>helper|Educatonal rules only; not clinically<br>validated|
|Federated learning|Sample-weighted aggregaton, a pluggable update<br>callback, a Gaussian diferental-privacy experiment,|No secure aggregaton or formal<br>privacy accountant|



Page 4 of 34 

_MedIntelOS — Technical Report_ 

|**Pillar**|**What is implemented**|**Explicit boundary**|
|---|---|---|
||basic outlier detecton||
|Audit|An in-memory SHA-256 hash chain over structured<br>entries|Tamper-evident within one process;<br>not durable or externally anchored|
|Consent|Solidity consent and audit-ledger contracts with<br>Hardhat tests|Identty, legal authority, erasure,<br>governance, and key custody remain<br>of-chain|
|Operatons|Docker, Compose, CI, lintng, tests, generated API<br>documentaton|Producton infrastructure is out of<br>scope|



### **1.2 Why a Unified Codebase Is a Meaningful Design Choice** 

A skeptical reading might ask why interoperability, decision support, federated learning, audit, and consent belong in the same repository at all, given that production deployments will typically source each capability from a different vendor or subsystem. The answer the codebase implicitly gives is pedagogical and architectural rather than operational: by keeping the five concerns in one place but behind clean module boundaries — a FastAPI process (‘api/app.py’) that depends on, but does not entangle, ‘fhir/’, ‘cdss.py’, ‘audit.py’, and ‘federated.py’, plus a wholly separate Solidity codebase for consent — the project offers a single place to study how these systems' data contracts meet at runtime. The architecture diagram in Section 3 makes this composition, and the fact that no module directly calls into another's internals, visible. 

Page 5 of 34 

_MedIntelOS — Technical Report_ 

## **2. Standards and Research Context** 

MedIntelOS positions itself relative to four independent bodies of standards and research practice: HL7's Fast Healthcare Interoperability Resources (FHIR), the CDS Hooks specification for embedding decision support inside clinical workflows, the federated-learning and differential-privacy literature that emerged from cross-institution machine learning research, and the smart-contract patterns used for programmable consent in distributed-ledger systems. Understanding the codebase requires understanding what each standard promises, and precisely which slice of that promise the repository chooses to implement. 

### **2.1 FHIR Release 5** 

FHIR, published by HL7 as a family of resource definitions and RESTful interaction patterns, is the dominant interoperability standard for health data exchange. Release 5 (version 5.0.0) extends earlier releases with refinements to resource definitions and search behavior. A conformant FHIR server must support capability discovery, resource validation against structure definitions and profiles, terminology binding, and a broad RESTful and search interaction surface. MedIntelOS implements a narrow, explicitly-scoped subset of this surface — JSON resource construction, create/read/update/delete against an in-memory store, version tracking through ‘meta.versionId’, optimistic concurrency through weak ETags and ‘IfMatch’, and a ‘CapabilityStatement’ that accurately advertises only what is implemented. This is a defensible research posture: rather than claiming conformance it cannot support, the project treats the FHIR resource shape as a well-understood data contract worth reusing, while being explicit that persistence, profile validation, and terminology services are replacement points for any real deployment. 

### **2.2 CDS Hooks** 

CDS Hooks defines how a clinical system invokes an external decision-support service at specific workflow moments — for example, when a clinician opens a patient's chart (‘patient-view’) or is about to sign an order (‘order-sign’) — and how that service returns structured “cards” containing advisory information, links, and suggested actions. MedIntelOS implements the discovery endpoint (‘/cds-services’) and a ‘patient-view’ service, and shapes its CDSS output as CDS Hooks cards augmented with a namespaced ‘_medintelos’ extension carrying rule-level explanation data. The project is explicit that its prefetch context is project-specific rather than a certified integration path, which matters because CDS Hooks conformance is what allows a decision-support service to be safely reused across unrelated EHR vendors. 

### **2.3 Federated Learning and Differential Privacy** 

Federated learning allows multiple institutions to jointly improve a shared model without centralizing raw patient data: each site computes an update locally, and only the update — not the underlying data — is transmitted to a coordinator for aggregation, most commonly through a sample-weighted averaging scheme such as FedAvg. Differential privacy adds a further guarantee: by clipping each contribution's influence and adding calibrated noise before aggregation, it becomes possible to bound how much any single update can reveal about the data that produced it, typically expressed through a privacy budget 

Page 6 of 34 

_MedIntelOS — Technical Report_ 

pair (ε, δ). MedIntelOS's federated module implements the mechanical core of both ideas — weighted aggregation and a Gaussian noise mechanism with configurable ε, δ, gradient-clipping norm, and noise multiplier — while being explicit that it does not implement a formal privacy accountant, secure aggregation, or transport-layer authentication, all of which a production federated system requires to make its differential-privacy claims operationally meaningful. 

### **2.4 Programmable Consent on a Distributed Ledger** 

A recurring proposal in health-data governance research is to use smart contracts to make patient consent auditable, granular, and revocable, while keeping the protected data itself off-chain. MedIntelOS's Solidity contracts follow this pattern closely: consent is scoped per FHIR resource type and purpose (treatment, research, public health, payment), time-bounded, revocable, and supported by proxy-consent and emergency-override paths, with every state transition logged to a companion audit-ledger contract. The design documentation is careful to note what a smart contract cannot provide on its own — legal identity binding, guardianship verification, purpose enforcement outside the contract's own logic, and genuine data erasure, since blockchain history is append-only by construction. 

### **2.5 Positioning Summary** 

|**Standard / research area**|**MedIntelOS's implemented slice**|**What is deliberately deferred**|
|---|---|---|
|HL7 FHIR R5|Resource JSON shape, CRUD, versioning,<br>ETags, CapabilityStatement|Profle & terminology validaton,<br>persistence, Bulk Data, SMART launch|
|CDS Hooks|Discovery + patent-view service, card-<br>shaped responses|Certfed prefetch context, order-<br>select/order-sign conformance|
|Federated learning / DP|Weighted aggregaton, Gaussian<br>mechanism, outlier check|Formal privacy accountant, secure<br>aggregaton, signed transport|
|Consent smart contracts|Scoped, tme-bounded, revocable consent +<br>audit ledger|Identty binding, governance, true<br>erasure, key custody|



Page 7 of 34 



<!-- Start of picture text -->
External Actors<br>EHR<br>/ Reseach lent Federated Participant Sites<br>Consent Layer (Solidity) FastAPI Boundary (medintelos.api.app)<br>MeatneloSConsentange<br>.<br>MedintelOSAuditLedger Size-LimitMiddleware +i  Security-Header<br>Domain Modules (src/medintelos)<br>Routes: FHIR CRUD, CDS FederatedCoordinator<br>Hooks, CDSS Evaluate Weighted aggregation<br>SSSSS<br>an bo<br>FHIRStore CDSSEngine AuditChain<br>In-memory JSON repository RiskScorer + Alerts SHA-256 hash chain<br><!-- End of picture text -->



<!-- Start of picture text -->
api/app.py federated.py contracts/MedIntelOSConsent.sol<br>a =<br>mney ieepostonyay )<br>fhir/builders.py 7 config.py<br><!-- End of picture text -->

_MedIntelOS — Technical Report_ 

‘Settings’ object rather than reading global configuration, which is what makes the module boundary testable rather than merely aspirational. 

Page 10 of 34 

_MedIntelOS — Technical Report_ 

## **4. The FHIR R5 Interoperability Layer** 

The interoperability layer is centered on two collaborating components: ‘FHIRBundleBuilder’ and related functions in ‘fhir/builders.py’, which construct well-formed FHIR JSON resources and a ‘CapabilityStatement’; and ‘FHIRStore’ in ‘fhir/repository.py’, which owns the in-memory persistence, versioning, and search behavior. The API layer never manipulates raw resource dictionaries directly — every request passes through the store's typed interface, which is what allows the resource-type/URL consistency check, version increment, and audit emission to be enforced in one place regardless of which route triggered them. 

### **4.1 Resource Lifecycle and Optimistic Concurrency** 

Figure 3 traces a create-then-update sequence end-to-end. On creation, ‘FHIRStore’ validates that the URL's resource type matches the payload's ‘resourceType’ field, assigns a server-generated identifier, sets ‘meta.versionId’ to 1, and appends a corresponding entry to the audit chain before returning a 201 response with a weak ETag. On update, the client is expected to supply an ‘If-Match’ header carrying the version it last observed; the store compares this against the currently stored ‘versionId’ and raises a ‘VersionConflict’, mapped by the API layer to an HTTP 409 response with a FHIR ‘OperationOutcome’ body, whenever the two disagree. This is the standard optimistic-concurrency pattern FHIR servers use to prevent silent lost updates when two clients race to modify the same resource, implemented here without a database transaction because the store itself is single-process and lock-protected. 

Page 11 of 34 



<!-- Start of picture text -->
APIKeyAuthenticator FHIRStore AuditChain<br>POST /fhir/R5/Patient (X-API-Key)<br>hmac.compare_digest(key, expected)<br>401 if invalid<br>create(resourceType, body)<br>validate resoufceType match<br>assign id, mefa.versionId=1<br>append(actor, "create", resource)<br>AuditEntry(entry_hash)<br>201 Created + ETag (weak)<br>PUT /fhir/R5/Patient/ {jd} (If-Match)<br>compare If-Matchjto stored versionId<br>"i —aiaeiaceaae eae =o eae as SENSES URE LASS SST SSE LSE TET E<br>‘ 409 VersionCgnflict ;<br>i incremenf versionId :<br>i append(actor, "update", resource) i<br>i 200 OK + new ETag :<br>APIKeyAuthenticator FHIRStore AuditChain<br><!-- End of picture text -->

_MedIntelOS — Technical Report_ 

returns a ‘CapabilityStatement’ generated from the same code that implements the behavior it describes, which is a meaningful correctness property: a CapabilityStatement is only useful to an integrating client if it does not overstate what the server can do, and generating it programmatically from the implemented route set is one concrete way to keep the two in sync. 

### **4.4 Example Interaction** 

Creating a synthetic FHIR Patient resource against the reference API illustrates the full request shape: 

POST /fhir/R5/Patient HTTP/1.1 Content-Type: application/fhir+json X-API-Key: <development key> 

{"resourceType": "Patient", "name": [{"family": "Doe"}], "gender": "unknown"} 

HTTP/1.1 201 Created ETag: W/"1" Location: /fhir/R5/Patient/<generated-id> 

### **4.5 Boundary Summary** 

|**Capability**|**Status**|
|---|---|
|Resource CRUD with server-assigned IDs|Implemented|
|Optmistc concurrency via If-Match / ETag|Implemented|
|CapabilityStatement generaton|Implemented|
|Exact-match search subset|Implemented|
|Profle / StructureDefniton validaton|Not implemented|
|Terminology binding and validaton|Not implemented|
|Durable persistence across process restarts|Not implemented|
|Bulk Data / subscriptons / SMART App Launch|Not implemented|



Page 13 of 34 



<!-- Start of picture text -->
+ @sora<br>>| News? || ———————w —<br>(PatientContextCDSSRequest JSON) Pydantic_t0_domaing)to dataclass vitals, PatientContextlabs, meds, diagnoses a] (StaticRiskScorerrule methods) value,List{RiskScore]level, explanation |. cpsstngine.evaluate() +| priority,List{ClinicalAler]overridable — [ + _medintelosCDS Hooks extension Cards >|[if ISON Response<br>a ——— = i >| KDIGOAKI SS — ee<br>*)  CHAZDS2-VASc<br><!-- End of picture text -->



_MedIntelOS — Technical Report_ 

path as “what did this alert compute,” rather than approximated by a post hoc feature-attribution method as is common with opaque machine-learning scorers. 

### **5.2 Alert Construction and Fatigue Reduction** 

‘CDSSEngine.evaluate’ converts risk scores that cross a clinically meaningful threshold into ‘ClinicalAlert’ objects carrying an ‘AlertPriority’ (info, warning, critical, or override_required), an ‘overridable’ flag, and a list of acceptable override reasons. A dedicated ‘_apply_fatigue_reduction’ step and a ‘record_override’ method exist specifically to address alert fatigue — the well-documented phenomenon in which clinicians begin to ignore decision-support output once its volume or false-positive rate exceeds a usable threshold — by allowing prior overrides to influence whether a subsequent, similarly-shaped alert should still interrupt the workflow. 

### **5.3 Drug Interaction Checking** 

A separate ‘DrugInteractionEngine’ class provides interaction checking over a deliberately small, example medication set. The README is explicit that this drug knowledge base is “educational rules only” and that the medication set is small by design, in contrast to a licensed, continuously-maintained drug knowledge base (of the kind commercial CDS vendors integrate) that any real deployment would require. 

### **5.4 From Alerts to CDS Hooks Cards** 

The final pipeline stage, ‘_alert_to_cds_card’, maps each ‘ClinicalAlert’ onto the CDS Hooks card shape — ‘summary’, ‘indicator’, ‘source’, ‘suggestions’, and ‘links’ — while attaching the underlying ‘RiskScore’ explanation under a ‘_medintelos’ namespaced extension field, which keeps the response schema-valid for CDS Hooks consumers that ignore unrecognized extensions while still surfacing the full rule-level detail to consumers that understand it. The README notes that certain optional CDS Hooks fields are intentionally omitted “where the integration path requires stricter CDS Hooks conformance,” again reflecting the project's preference for an accurate, narrower claim over an inflated one. 

### **5.5 Explicit Clinical-Use Boundary** 

Every scoring method's docstring repeats a variant of the same caution present at the top of the ‘RiskScorer’ class: these are “educational implementations of published clinical scoring rules” that “have not been clinically validated as a software system and must not be used for diagnosis or treatment decisions.” This is reinforced repository-wide by a dedicated ‘MEDICAL_DISCLAIMER.md’ file. The distinction being drawn is between the clinical validity of the underlying published rule — qSOFA and NEWS2 are both well-studied instruments — and the software-validation status of this particular implementation, which has not undergone the analytical and clinical validation, human-factors testing, or regulatory review that would be required before any such implementation could be trusted at the bedside. 

Page 15 of 34 



<!-- Start of picture text -->
a aaniaiiill<br>start_round(rpund_number)<br>update_provider(participant, round_id, global_model)<br>update_provider(participant, round_id, globhl_model)<br>ModelUpdate(weights, num_samples, loss)<br>ModelUpdate(weights, num_samples,|loss)<br>validate shapes, layer names, round_id<br>outlier detection|(norm threshold)<br>[opt ) [DP enabled] H<br>i clip(weights, mak_grad_norm) |<br>i add Gaussian nojse(epsilon, delta) H<br>aggregate(updates weighted by num_safmples)<br>neW global_model, aggregated_logs<br>round.status =||COMPLETED<br>cn Ee<br><!-- End of picture text -->

_MedIntelOS — Technical Report_ 

comment clarifies that the proximal term is understood to modify the participant's local training objective, while server-side aggregation itself remains ordinary sample-weighted averaging. 

### **6.2 Differential Privacy via a Gaussian Mechanism** 

The ‘GaussianMechanism’ class implements the standard two-step (ε, δ)-differential-privacy recipe for aggregated updates: gradient clipping followed by calibrated Gaussian noise. Clipping rescales each participant's combined weight tensor so its L2 norm does not exceed a configured ‘max_grad_norm’; noise is then drawn from a normal distribution whose standard deviation is the product of a ‘noise_multiplier’ and a sensitivity term computed as ‘2 × max_grad_norm / num_participants’. Both steps are visible in the module and reproduced below in simplified form: 

clip_coef = min(1.0, max_grad_norm / (total_norm + 1e-8)) clipped   = weights * clip_coef 

sensitivity = 2.0 * max_grad_norm / num_participants noise_std   = noise_multiplier * sensitivity noised      = clipped + Normal(0, noise_std) 

This is the correct mechanical shape of the Gaussian mechanism used throughout the differential-privacy literature, and the ‘DifferentialPrivacyConfig’ dataclass validates its own parameters on construction — rejecting non-positive ε, a δ outside (0, 1), a non-positive clipping norm, and a negative noise multiplier. What the module does not provide is a formal privacy accountant that tracks cumulative privacy loss across many rounds (for example, via moments accounting or Rényi differential privacy composition), nor a proof that the sampling procedure feeding the mechanism satisfies the independence assumptions the Gaussian mechanism's guarantees rely on. The architecture documentation labels this explicitly as “an experiment, not a complete DP system,” a distinction this report preserves. 

### **6.3 Byzantine-Participant Detection** 

A ‘detect_byzantine’ method screens incoming updates using cosine similarity and L2-norm outlier statistics, flagging a participant when its update's norm deviates from the round's distribution by more than a configured z-score threshold. Detected participants have their persistent ‘trust_score’ multiplicatively decayed (by a factor of 0.5 per detection in the observed logic), which is used elsewhere in the coordinator to gate future round eligibility. This is a heuristic, statistical defense rather than a cryptographic or game-theoretic one: it can catch a participant whose update is a gross statistical outlier, but it is not designed to withstand an adaptive adversary who shapes an update specifically to evade norm-based detection, which is why the threat-model documentation lists “a dishonest majority of federated participants” among the repository's explicit non-goals. 

Page 17 of 34 



<!-- Start of picture text -->
iealnoasann smax_grad_norm |l NO, sigmar2y L (HMAC signature) J | ; Updated global model<br>broadcast<br><!-- End of picture text -->





<!-- Start of picture text -->
AuditChain.verify()<br>Recompute digest per entry<br>previous_hashGeares= 0x00..00 SHA-256(payload_1)Entryaid 1 previous_hash SHA-256(payload_2)Entryrc 2 previous_hash: SHA-256(payload_3)Entryapi 3 previous_hash: SHA-256(payload_n)Entale > hmac.ciiiastored)digestcs ted,al<br>Check previous_hash linkage<br><!-- End of picture text -->

_MedIntelOS — Technical Report_ 

### **7.3 What “Tamper-Evident” Does and Does Not Mean Here** 

It is important to be precise about the security property this module actually provides, because “hash chain” is sometimes read as a stronger claim than is warranted here. Because both the entries and the verification logic live in the same process's memory, an attacker with the ability to modify that process's in-memory state — for instance, through a code-execution vulnerability elsewhere in the same process — could in principle rewrite the entire list of entries and recompute every digest consistently, producing a chain that verifies successfully despite having been fabricated after the fact. The chain protects against accidental or unsophisticated tampering, and it is the correct data structure to sit underneath a durable, append-only, externally-anchored store; it is not, by itself, evidence of integrity against a fully compromised host. The architecture and threat-model documentation says exactly this: a production implementation “needs an append-only durable sink, access controls, retention policy, clock strategy, external anchoring, monitoring, and tested recovery,” and a compromised host is listed explicitly among the system's non-goals. 

### **7.4 Minimal Metadata by Design** 

The threat-model documentation notes that “audit stores action metadata only” and that request bodies are deliberately excluded from log entries, which limits the audit chain's own exposure as a secondary source of sensitive data — an audit log that faithfully records clinical payloads becomes, itself, a highvalue target and a HIPAA-relevant asset. The trade-off is that a metadata-only chain can prove that an action of a given type occurred against a given resource at a given time, but cannot on its own reconstruct the full content of what changed; a real deployment pairs it with a separate, access-controlled record of resource history for that purpose. 

Page 20 of 34 



<!-- Start of picture text -->
grantConsent() /<br>grantProxyConsent()<br>_finalizeGrant()\n(institution<br>verified)<br>revokeConsent()— block.timestamp > expiresAt executeGDPRErasure()\n(activateEmergenc!”. were— ad<br>chain only)<br>©<br><!-- End of picture text -->

_MedIntelOS — Technical Report_ 

the contract will not honor once ‘expiresAt’ has passed. ‘verifyConsent’ is the read path a relying party calls before acting on a consent claim, checking status, purpose, scope, and expiry together rather than any one of them in isolation. 

### **8.3 Proxy Consent and Emergency Access** 

‘setProxyAuthorization’ and ‘grantProxyConsent’ implement a path for consent to be granted on behalf of a patient by an authorized proxy — relevant for minors or incapacitated patients — while ‘activateEmergencyOverride’ implements a bounded emergency-access path for a verified clinician at a verified institution to obtain access to an unconscious or critical patient's record outside the normal consent flow. Every emergency override the contract observes carries an immutable, on-chain justification string and expires automatically 24 hours after activation (‘EMERGENCY_OVERRIDE_DURATION’), which bounds the blast radius of the override without requiring a separate manual revocation step. 

### **8.4 GDPR Erasure: What the Chain Can and Cannot Do** 

‘executeGDPRErasure’ records a caller-supplied erasure-proof hash and, if the target consent is currently active, revokes it with the reason “GDPR Art. 17 Right to Erasure.” This is a carefully bounded function: it marks that an erasure was requested and asserted, and it removes the consent's active authorization going forward, but it cannot delete the historical blockchain record of the consent ever having existed, because a public or permissioned ledger's append-only history is, by construction, not erasable. The deployment documentation states this without hedging: the contract “records erasure evidence; it cannot erase off-chain replicas or immutable blockchain history,” and explicitly instructs that this event must not be marketed as proof of legal erasure. This is precisely why the architecture documentation forbids placing PHI, names, identifiers, or raw FHIR resources on-chain in the first place — even a hash of such data, once written to an immutable ledger, creates a permanent linkage and retention risk that GDPR-style erasure rights cannot subsequently unwind. 

### **8.5 Interfaces That Signal Intended Extensions** 

The contract declares an ‘IConsentVerifier’ interface for verifying a zero-knowledge proof of consent without revealing patient identity, and an ‘IAuditLedger’ interface implemented by the companion auditledger contract. Declaring the ZK-verifier interface without a corresponding on-chain circuit implementation is a common and legitimate pattern for signaling an intended extension point — privacypreserving consent verification is an active research area — while keeping the currently-shipped contract self-contained and auditable. 

### **8.6 Boundary Summary** 

|**Capability**|**Status**|
|---|---|
|Scoped, purpose-tagged, tme-bounded consent grants|Implemented|



Page 22 of 34 

_MedIntelOS — Technical Report_ 

|**Capability**|**Status**|
|---|---|
|Revocaton, expiry, and GDPR erasure marking|Implemented|
|Proxy consent and bounded emergency override|Implemented|
|On-chain audit ledger of consent events|Implemented|
|Zero-knowledge consent verifcaton|Interface declared, not implemented|
|Legal identty binding / guardianship verifcaton|Out of scope (of-chain requirement)|
|True (retroactve) data erasure from ledger history|Not possible by constructon|
|Independent security audit / formal verifcaton|Not performed within this repository|



Page 23 of 34 



<!-- Start of picture text -->
Trust Boundary: Federated Participant<br>Hospital / Clinic Node<br>ModelUpdate<br>Trust Boundary: Aggregation Service Trust Boundary: Client<br>FederatedCoordinator HTTP Client<br>wallet tx API key<br>rust Boundary: Blockchain Trust Boundary: API Process<br>Consent + Audit Contracts FastAPI + Auth + CDSS<br>Trust Boundary: Observability Trust Boundary: FHIR Persistence<br>Logs / SIEM FHIRStore (in-memory)<br><!-- End of picture text -->

_MedIntelOS — Technical Report_ 

|**Threat**|**Reference mitgaton (implemented)**|**Required deployment work**|
|---|---|---|
|Unauthorized API access|Constant-tme API-key comparison|OIDC, scopes, MFA, rotaton, rate limits|
|Resource overwrite|If-Match version checks|Durable transactons, authorizaton, history,<br>backups|
|Sensitve logging|Audit stores metadata only, not bodies|Log review, redacton tests, SIEM access<br>policy|
|Malicious model update|Shape checks, norm outlier detecton|Signatures, atestaton, robust aggregaton,<br>quarantne|
|Privacy leakage from<br>models|Optonal clip/noise experiment|Formal accountant, sampling proof, privacy<br>review|
|Smart-contract privilege<br>abuse|Owner checks, explicit proxy<br>authorizaton|Multsig, tmelocks, monitoring,<br>independent audit|
|On-chain privacy leakage|Documentaton prohibits PHI on-chain|Data classifcaton, linkage analysis,<br>retenton design|
|Clinical automaton bias|Explicit warnings, deterministc<br>explanatons|Human-factors testng, governance, override<br>review|
|Denial of service|Body-size limit, bounded request lists|Gateway limits, queues, autoscaling, circuit<br>breakers|



### **9.3 The Authentication Boundary in Detail** 

‘security.py’ implements the entirety of the reference API's authentication as a single, 25-line ‘APIKeyAuthenticator’ dependency: it compares the caller-supplied ‘X-API-Key’ header against a configured value using ‘hmac.compare_digest’, a constant-time comparison chosen specifically to prevent a timing side-channel from letting an attacker recover the key byte by byte. The README describes this static key as intentional: “the demo API uses a static API key so the authentication boundary is visible,” and ‘docs/DEPLOYMENT.md’ notes that production mode refuses the built-in development key and requires a minimum 24-character replacement — a configuration guard, explicitly not described as a credential-management solution. This kind of self-limiting language recurs throughout the securityrelevant documentation and is, in the authors' own words, only a floor above which OIDC/OAuth 2.0, short-lived credentials, and tenant isolation are still required. 

### **9.4 Explicit Non-Goals** 

The threat model closes with a list of scenarios the repository does not defend against: a compromised host, a malicious maintainer, stolen deployment keys, supply-chain compromise, traffic analysis, a dishonest majority of federated participants, and coercion of blockchain participants. Naming these explicitly is itself a security-engineering best practice — a threat model that only lists what a system 

Page 25 of 34 

_MedIntelOS — Technical Report_ 

defends against, without also stating what it does not, tends to be read (incorrectly) as exhaustive by downstream integrators. 

### **9.5 Review Checklist** 

Before any deployment, the documentation requires that an operator document data flows, lawful basis, retention, tenant boundaries, emergency access, key custody, dependency provenance, incident response, disaster recovery, clinical ownership, and rollback authority — a checklist that functions less as a feature of the software and more as an explicit hand-off contract between the reference implementation and whatever governance process would need to exist around a real deployment. 

Page 26 of 34 



<!-- Start of picture text -->
Reference Deployment (Docker Compose)<br>MedintelOS container<br>non-root, read-only rootfs<br>dropped capabilities<br>8080<br>Uvicomn / FastAPI replace replace replace<br>replace replace replace<br>Required Production Replacements<br>OIDC/OAuth2 Authorization Conformance-tested FHIR Mutually-authenticated FL Robust aggregation +<br>Server repository Durable audit + SIEM pipeline , transport adversarial defense Reviewed multisig governance<br><!-- End of picture text -->



_MedIntelOS — Technical Report_ 

|**Variable**|**Purpose**|**Default**|
|---|---|---|
|BYTES|middleware||



‘Settings.validate()’ is invoked at application-factory time and enforces the production-mode guard mentioned in Section 9.3: a non-development environment must not run with the built-in development API key, and any replacement key must be at least 24 characters. This validation runs before the FastAPI app is constructed, which means a misconfigured production deployment fails fast at startup rather than silently accepting an unsafe credential at request time. 

### **10.3 Contract Deployment Sequence** 

The README specifies a fixed four-step sequence for deploying the consent layer, reproduced here: 

1. Deploy MedIntelOSAuditLedger with the zero address. 

2. Deploy MedIntelOSConsentManager with the ledger address. 

3. Call setConsentManager on the ledger. 

4. Register and independently verify institution identities. 

The ordering matters: the audit ledger must exist before the consent manager can be told to log into it, and the ledger must in turn be told which consent-manager address is authorized to write to it, closing a circular dependency in a specific, replayable order. ‘docs/DEPLOYMENT.md’ further recommends pinning compiler and dependency hashes, running static analysis, commissioning an independent audit, defining an upgrade and pause strategy, using a multisig administrator, and testing key loss before any contract deployment beyond a development chain. 

### **10.4 Continuous Integration** 

The GitHub Actions workflow referenced by the README badge runs Python linting (‘ruff’) and the test suite (‘pytest’) on every change, with contract tests — the Hardhat/Viem suite in ‘contract-tests/’ — executed in a separate CI job appropriate to their different toolchain. ‘mypy’ is available as an additional, stricter static-typing check invoked through the project's quality-check commands (‘ruff check .’, ‘pytest’, ‘mypy src/medintelos’) but is described as available rather than gating, leaving type-strictness as a developer-invoked check rather than a hard CI requirement. 

Page 28 of 34 

_MedIntelOS — Technical Report_ 

## **11. Validation Strategy and Evidentiary Gaps** 

‘docs/VALIDATION.md’ opens with a sentence that could stand as an epigraph for the whole repository: “the automated suite verifies software behavior, not clinical safety.” This section separates the two categories the documentation itself distinguishes — evidence the repository already provides, and evidence a clinical deployment would still need to generate — and relates each to the modules examined in Sections 4 through 8. 

### **11.1 Automated Evidence Present in the Repository** 

- Unit tests covering score thresholds and missing/zero-value threshold behavior in the CDSS scoring rules (‘test_cdss.py’). 

- Unit tests covering the FHIR resource lifecycle and optimistic locking, including version-conflict paths (‘test_fhir.py’). 

- Unit tests covering federated aggregation math, including shape and layer-name validation (‘test_federated.py’). 

- Unit tests covering audit chaining and tamper detection (‘test_audit.py’). 

- API-level tests covering authentication, FHIR CRUD/search, audit emission, and CDSS response shape (‘test_api.py’). 

- Static analysis via ‘ruff’ for correctness and style, and ‘mypy’ as an optional stricter type check. 

- Solidity compilation via ‘solc’ and Hardhat/Viem integration tests exercising the consent lifecycle in CI. 

### **11.2 Evidence Required Before Any Clinical Use** 

The documentation is unusually specific about what falls outside this evidence base, listing eleven distinct categories of work: requirements traceability, hazard analysis, clinical association, analytical and clinical validation, representative datasets, subgroup analysis, calibration, human-factors studies, cybersecurity testing, data-governance review, change control, post-market monitoring, and jurisdiction-specific regulatory review. Table 6 organizes these against the pillar of the system each would primarily apply to, which is useful for a reader assessing how much distance separates “passes the test suite” from “safe to use on a real patient.” 

|**Pillar**|**Automated evidence present**|**Evidence stll required for clinical use**|
|---|---|---|
|CDSS scoring|Threshold unit tests, deterministc<br>explanaton output|Clinical associaton study, calibraton, hazard<br>analysis, human-factors testng|
|FHIR layer|Lifecycle and concurrency unit/API tests|Profle/terminology conformance testng,<br>durability testng|
|Federated learning|Aggregaton-math unit tests|Formal privacy accountng, adversarial|



Page 29 of 34 

_MedIntelOS — Technical Report_ 

|**Pillar**|**Automated evidence present**|**Evidence stll required for clinical use**<br>robustness evaluaton|
|---|---|---|
|Audit chain|Tamper-detecton unit tests|Durable-storage and external-anchoring<br>integrity testng|
|Consent contracts|Hardhat/Viem lifecycle integraton tests|Independent security audit, legal review of<br>enforceability|



### **11.3 The Software/Clinical Distinction, Restated** 

The recurring rhetorical move across the validation, threat-model, and architecture documents is to separate two questions that are easy to conflate: “does this code do what it says it does” and “is it safe to act on clinically.” The test suite examined above provides real, checkable evidence for the first question — for example, that ‘news2’ assigns the documented point bands to the documented vital-sign ranges, or that ‘FHIRStore.update’ correctly rejects a stale ‘If-Match’ header. It provides no evidence at all for the second question, and the documentation never implies otherwise. This is a methodologically sound position for an educational reference implementation to take, and it is one this report adopts as well: the analysis in this document is a software and architecture analysis, not a clinical-safety endorsement. 

Page 30 of 34 

_MedIntelOS — Technical Report_ 

## **12. Limitations, Ethics, and Future Work** 

This section consolidates the boundary statements scattered across earlier sections into a single view, then discusses the ethical considerations specific to a system that touches clinical decision support, crossinstitution model training, and irrevocable ledger writes at once, and closes with directions a continuation of this work could reasonably pursue. 

### **12.1 Consolidated Limitations** 

|**Area**|**Limitaton**|
|---|---|
|Persistence|The FHIR store is in-memory; all data is lost at process exit and must never hold protected<br>health informaton.|
|Authentcaton|The reference API uses a single statc API key rather than an identty-provider-backed<br>scheme with scopes and rotaton.|
|Clinical validity|Scoring rules are educatonal implementatons of published instruments, not clinically<br>validated sofware.|
|Drug knowledge|The interacton-checking medicaton set is deliberately small and not a licensed,<br>maintained knowledge base.|
|Privacy accountng|The diferental-privacy mechanism lacks a formal accountant tracking cumulatve privacy<br>loss across rounds.|
|Aggregaton security|Aggregaton is not cryptographically secure; a compromised or Byzantne transport is out<br>of scope.|
|Audit durability|The audit chain is tamper-evident only within a single running process, not durable or<br>externally anchored.|
|Consent enforceability|Legal identty binding, guardianship, and purpose enforcement outside the contract's own<br>logic remain of-chain.|
|Erasure|On-chain history cannot be retroactvely deleted; GDPR-style erasure can only be marked,<br>not truly executed on-chain.|



### **12.2 Ethical Considerations** 

Three ethical themes are worth naming explicitly, because they are the ones a system spanning decision support, federated learning, and consent tends to raise jointly rather than in isolation. First, automation bias: a clinician who repeatedly sees accurate-seeming, well-explained alerts may over-trust a system whose underlying rules have not been validated as software, which is precisely why the threat model lists “clinical automation bias” as a named threat requiring human-factors testing and governance rather than a purely technical mitigation. Second, federated learning does not eliminate privacy risk merely by keeping data local; without a formal privacy accountant, repeated rounds of model updates can leak more about 

Page 31 of 34 

_MedIntelOS — Technical Report_ 

a site's underlying population than any single round's differential-privacy parameters would suggest in isolation — a composition risk the documentation acknowledges but does not yet close. Third, consent recorded on an immutable ledger creates a durability asymmetry: revoking access is easy, but the historical fact that a person once granted (and perhaps later regretted granting) a particular consent persists forever in a form no contract can delete, which is why the project's own documentation is emphatic that no identifying or clinical data should ever be written on-chain, even in hashed form. 

### **12.3 Directions for Future Work** 

- Formal privacy accounting (e.g., Rényi differential privacy composition) layered on top of the existing Gaussian mechanism to bound cumulative privacy loss across many federated rounds. 

- A pluggable, conformance-tested FHIR persistence backend to replace the in-memory store, enabling profile and terminology validation without changing the API surface consumers depend on. 

- An independent security audit and, where feasible, formal verification of the Solidity consent and audit-ledger contracts prior to any deployment beyond a development chain. 

- A durable, externally-anchored audit sink (for example, periodic Merkle-root anchoring to a public ledger) to extend the existing in-process hash chain's tamper-evidence guarantee beyond a single running process. 

- Expansion of the clinical scoring library alongside a documented process for sourcing, versioning, and reviewing new rules against published literature, paired with prospective clinical validation before any rule is used outside an educational context. 

- A reference implementation of the declared ‘IConsentVerifier’ zero-knowledge interface, to demonstrate consent verification that does not require revealing patient identity even to the verifying contract. 

Page 32 of 34 

_MedIntelOS — Technical Report_ 

## **13. Conclusion** 

MedIntelOS is best understood not as a product but as a worked answer to a systems-design question: what does it look like to reason about interoperability, explainable decision support, privacy-preserving multi-institution learning, tamper-evident provenance, and patient-mediated consent as a single, coherently bounded problem, rather than as five unrelated procurement decisions? Across the ten diagrams and analysis presented in this report, three properties of the codebase stand out as genuinely instructive, independent of the project's alpha status. First, its module boundaries are real rather than aspirational: the FHIR store, the CDSS engine, the audit chain, and the federated coordinator are composed only at the API layer, which is what makes each one independently testable and independently replaceable, exactly as the architecture documentation claims. Second, its explanations are structurally faithful rather than cosmetic: because each clinical rule builds its explanation dictionary from the same branches that compute its score, and because the audit chain's digest is computed over the same fields it records, the system's “why” outputs cannot silently drift from its “what” outputs. Third, and perhaps most distinctively, its documentation practices intellectual honesty as a design discipline: class names that could overstate a guarantee (‘SecureAggregator’) are corrected in their own docstrings, every clinical rule repeats that it has not been validated as software, and the deployment guide states plainly that a hash of protected data written to an immutable ledger is still a privacy liability, not a privacy solution. 

None of this substitutes for the clinical, regulatory, and security work a real deployment would require, and the repository does not claim otherwise. Its value, examined on its own terms, is as a compact, welldocumented illustration of how to build the connective tissue between health-data standards, explainable clinical rules, federated computation, provenance, and consent, while keeping an accurate, continuously visible account of exactly how far that connective tissue currently reaches — and exactly where a production system would need to extend it. 

## **14. References** 

HL7 International. FHIR Release 5 (v5.0.0). https://hl7.org/fhir/R5/ 

CDS Hooks Working Group. CDS Hooks Stable Specifications. https://cds-hooks.hl7.org/ 

HL7 International. SMART App Launch Implementation Guide. https://hl7.org/fhir/smart-app-launch/ 

- U.S. Department of Health and Human Services. HIPAA Security Rule Summary. https://www.hhs.gov/hipaa/forprofessionals/security/laws-regulations/ 

- Singer M, Deutschman CS, Seymour CW, et al. The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3). JAMA. 2016;315(8):801–810. 

- Royal College of Physicians. National Early Warning Score (NEWS) 2: Standardising the Assessment of Acute-Illness Severity in the NHS. 2017. 

Kidney Disease: Improving Global Outcomes (KDIGO) Acute Kidney Injury Work Group. KDIGO Clinical Practice Guideline for Acute Kidney Injury. Kidney Int Suppl. 2012;2(1):1–138. 

Page 33 of 34 

_MedIntelOS — Technical Report_ 

- Lip GYH, Nieuwlaat R, Pisters R, Lane DA, Crijns HJGM. Refining Clinical Risk Stratification for Predicting Stroke and Thromboembolism in Atrial Fibrillation Using a Novel Risk Factor-Based Approach (CHA₂DS₂-VASc). Chest. 2010;137(2):263–272. 

- McMahan HB, Moore E, Ramage D, Hampson S, y Arcas BA. Communication-Efficient Learning of Deep Networks from Decentralized Data (FedAvg). Proceedings of AISTATS. 2017. 

- Dwork C, Roth A. The Algorithmic Foundations of Differential Privacy. Foundations and Trends in Theoretical Computer Science. 2014. 

MedIntelOS Contributors. MedIntelOS: README, Architecture, Threat Model, Deployment Guide, and Validation Strategy. https://github.com/Ciprian-LocalPulse/MedIntelOS 

Page 34 of 34 

