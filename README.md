# 🏥 MedIntelOS — Medical Intelligence Operating System

<div align="center">
  <img src="assets/medintelos-stack-visualization.png" alt="MedIntelOS Stack Visualization" width="100%">
</div>


> **The world's first open-source, AI-native, blockchain-secured, interoperable Medical Intelligence Operating System — built to unify clinical decision support, real-time patient monitoring, federated learning across hospitals, and zero-trust health data governance into a single, production-ready platform.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![FHIR R5](https://img.shields.io/badge/FHIR-R5%20Compliant-green)](https://hl7.org/fhir/)
[![HL7](https://img.shields.io/badge/HL7-v2%20%7C%20v3%20%7C%20CDA-orange)](https://www.hl7.org/)
[![HIPAA](https://img.shields.io/badge/HIPAA-Compliant%20Architecture-red)](docs/compliance/HIPAA.md)
[![GDPR](https://img.shields.io/badge/GDPR-Article%209%20Ready-blueviolet)](docs/compliance/GDPR.md)
[![ISO 13485](https://img.shields.io/badge/ISO%2013485-Medical%20Device%20QMS-lightgrey)](docs/compliance/ISO13485.md)
[![AI/ML](https://img.shields.io/badge/AI%2FML-Federated%20Learning-yellow)](src/ai/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## 🌍 What Makes MedIntelOS Unique

MedIntelOS is **not another EHR plugin or telemedicine app**. It is a full-stack medical operating layer that sits between hospital infrastructure, clinical staff, AI models, and patients — orchestrating everything in real time.

| Feature | Existing Solutions | MedIntelOS |
|---|---|---|
| Clinical AI | Siloed, vendor-locked | Open, federated, explainable |
| Interoperability | Partial FHIR adapters | Native FHIR R5 + HL7 + DICOM + OpenEHR |
| Data Governance | Centralized, breach-prone | Zero-knowledge proofs + blockchain audit |
| IoT Integration | Device-specific SDKs | Universal medical IoT mesh |
| Federated Learning | Research-only | Production-ready, privacy-preserving |
| Audit Trail | Log files | Immutable blockchain ledger |
| Decision Support | Alert fatigue tools | Context-aware, adaptive CDS |

---

## 🧠 Core Innovation: The MedIntel Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLINICIAN / PATIENT LAYER                     │
│          Web UI · Mobile App · Voice Interface · AR HUD          │
├─────────────────────────────────────────────────────────────────┤
│                    MEDINTELOS API GATEWAY                         │
│        REST · GraphQL · WebSocket · gRPC · FHIR R5 API           │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│   AI ENGINE  │  BLOCKCHAIN  │  IoT MESH    │  INTEROP ENGINE    │
│  Federated   │  Audit &     │  Real-time   │  FHIR·HL7·DICOM    │
│  Learning    │  Consent     │  Vitals      │  OpenEHR·ICD-11    │
│  CDSS · NLP  │  Smart Ctrct │  Wearables   │  SNOMED·LOINC      │
├──────────────┴──────────────┴──────────────┴────────────────────┤
│                  ZERO-TRUST SECURITY LAYER                        │
│       mTLS · ZKP · AES-256-GCM · HSM · RBAC · Audit Logs        │
├─────────────────────────────────────────────────────────────────┤
│                  DATA LAKE & ANALYTICS ENGINE                     │
│     PostgreSQL · TimescaleDB · IPFS · Apache Kafka · Spark       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Table of Contents

1. [Features](#-features)
2. [Architecture](#-architecture)
3. [Quick Start](#-quick-start)
4. [Installation](#-installation)
5. [Configuration](#-configuration)
6. [Modules](#-modules)
7. [API Reference](#-api-reference)
8. [AI & Machine Learning](#-ai--machine-learning)
9. [Blockchain & Audit](#-blockchain--audit)
10. [IoT Integration](#-iot-integration)
11. [Interoperability](#-interoperability)
12. [Security & Compliance](#-security--compliance)
13. [Deployment](#-deployment)
14. [Testing](#-testing)
15. [Contributing](#-contributing)
16. [Research & Publications](#-research--publications)
17. [Support & Donations](#-support--donations)
18. [License](#-license)

---

## ✨ Features

### 🤖 AI & Clinical Decision Support
- **Federated Learning Engine** — Train AI models across 100+ hospitals without sharing raw patient data
- **Real-time CDSS** — Context-aware alerts that learn from physician overrides (zero alert fatigue)
- **Medical NLP** — Extract structured data from clinical notes, discharge summaries, radiology reports
- **Predictive Analytics** — Sepsis, AKI, readmission, deterioration risk scoring (validated against MIMIC-IV)
- **Explainable AI** — Every prediction includes SHAP-based clinical reasoning
- **Drug Interaction Engine** — Real-time polypharmacy analysis with CYP450 pathway modeling
- **Imaging AI Connector** — DICOM-native integration with any imaging AI model (pathology, radiology)

### ⛓️ Blockchain & Data Governance
- **Immutable Audit Trail** — Every data access, modification, and consent logged on-chain
- **Patient Consent Smart Contracts** — Granular, revocable, time-bounded data sharing
- **Zero-Knowledge Proofs** — Verify patient identity and eligibility without revealing PHI
- **Cross-Institutional Trust** — Hospitals can query aggregate insights without data egress
- **GDPR Article 17 Automation** — Right-to-erasure workflows with cryptographic proof

### 📡 IoT & Real-Time Monitoring
- **Universal Medical IoT Mesh** — Connects any device via MQTT, CoAP, or proprietary protocols
- **Vital Sign Stream Processing** — Sub-100ms alert generation from continuous monitoring
- **Wearable Integration** — Apple Watch, Fitbit, Garmin, CGM devices, ECG patches
- **Smart ICU** — Automated ventilator, infusion pump, and bedside monitor data ingestion
- **Edge Computing** — Local AI inference on IoT gateways for offline-capable hospitals

### 🔄 Interoperability
- **FHIR R5 Native** — Complete resource implementation (400+ resource types)
- **HL7 v2/v3 Translator** — Bidirectional real-time message transformation
- **DICOM WADO/STOW** — Full imaging workflow support
- **OpenEHR Archetypes** — Clinical knowledge modeling with archetype designer
- **Terminology Services** — SNOMED CT, LOINC, ICD-11, RxNorm, NDC live mapping
- **CDS Hooks** — Standard integration with any EHR (Epic, Cerner, OpenMRS, OpenEMR)

### 🔐 Security
- **Zero-Trust Architecture** — No implicit trust, every request authenticated and authorized
- **End-to-End Encryption** — AES-256-GCM at rest, TLS 1.3 in transit, mTLS between services
- **Hardware Security Modules** — Key management via HSM or cloud KMS
- **RBAC + ABAC** — Fine-grained clinical role permissions
- **Threat Detection** — Anomaly detection on data access patterns
- **Penetration Testing Suite** — Built-in security test harness

---

## 🏗️ Architecture

See [docs/architecture/OVERVIEW.md](docs/architecture/OVERVIEW.md) for the full architecture deep-dive.

### Service Topology

```
medintelos/
├── api-gateway/          # Kong-based API gateway with medical auth
├── core/                 # Event bus, orchestration, state machine
├── ai-engine/            # Federated learning + CDSS + NLP
├── blockchain/           # Hyperledger Fabric nodes + smart contracts
├── iot-mesh/             # MQTT broker + device registry + stream processor
├── interop/              # FHIR R5 server + HL7 translator + DICOM proxy
├── analytics/            # Spark + TimescaleDB + real-time dashboards
├── security/             # ZKP, HSM, RBAC, threat detection
├── frontend/             # React clinical UI + mobile app
└── infrastructure/       # Kubernetes, Helm, Terraform, CI/CD
```

---

## 🚀 Quick Start

### Prerequisites
- Docker 24+ & Docker Compose v2
- Kubernetes 1.28+ (for production)
- Node.js 20 LTS
- Python 3.11+
- Go 1.21+
- 16GB RAM minimum (32GB recommended for full stack)

### 60-Second Demo

```bash
# Clone the repository
git clone https://github.com/Ciprian-LocalPulse/MedIntelOS.git
cd MedIntelOS

# Copy and configure environment
cp configs/.env.example configs/.env

# Start the full stack (demo mode with synthetic MIMIC-IV data)
docker compose -f infrastructure/docker/docker-compose.demo.yml up -d

# Wait for services to be healthy (approx 2 minutes)
./scripts/wait-for-healthy.sh

# Load synthetic patient data
./scripts/seed-demo-data.sh

# Open the clinical dashboard
open http://localhost:3000

# Open API documentation
open http://localhost:8080/api-docs

# Open monitoring dashboard
open http://localhost:9090  # Grafana
```

Default demo credentials:
- **Physician**: `dr.smith@demo.medintelos.io` / `Demo@2024!`
- **Nurse**: `nurse.jones@demo.medintelos.io` / `Demo@2024!`
- **Admin**: `admin@demo.medintelos.io` / `Admin@2024!`

---

## 📦 Installation

### Option 1: Docker Compose (Development)

```bash
git clone https://github.com/Ciprian-LocalPulse/MedIntelOS.git
cd MedIntelOS
cp configs/.env.example configs/.env
# Edit configs/.env with your settings
docker compose up -d
```

### Option 2: Kubernetes (Production)

```bash
# Add Helm repository
helm repo add medintelos https://charts.medintelos.io
helm repo update

# Install with production values
helm install medintelos medintelos/medintelos \
  --namespace medintelos \
  --create-namespace \
  --values configs/helm/production-values.yaml
```

### Option 3: Manual (Advanced)

See [docs/installation/MANUAL.md](docs/installation/MANUAL.md) for step-by-step manual installation.

---

## ⚙️ Configuration

All configuration is managed via environment variables and YAML config files.

```bash
configs/
├── .env.example              # All environment variables with documentation
├── medintelos.yaml           # Main application config
├── ai-engine.yaml            # AI/ML model configuration
├── blockchain.yaml           # Hyperledger Fabric network config
├── iot-mesh.yaml             # IoT device registry config
├── fhir-server.yaml          # FHIR R5 server config
├── security.yaml             # Security policies and ZKP params
└── helm/
    ├── values.yaml           # Default Helm values
    ├── production-values.yaml
    └── development-values.yaml
```

Key configuration parameters:

```yaml
# medintelos.yaml
medintelos:
  institution:
    name: "General Hospital"
    fhir_base_url: "https://fhir.yourhospital.org/R5"
    timezone: "UTC"
    
  ai:
    federated_learning:
      enabled: true
      aggregation_strategy: "FedProx"  # FedAvg | FedProx | SCAFFOLD
      differential_privacy:
        enabled: true
        epsilon: 1.0
        delta: 1e-5
    
  blockchain:
    network: "hyperledger-fabric"
    channel: "medintelos-main"
    consensus: "RAFT"
    
  security:
    zero_trust: true
    mfa_required: true
    session_timeout_minutes: 30
    audit_all_phi_access: true
```

---

## 📚 Modules

### 1. Core Engine (`src/core/`)
- **Event Bus** — Apache Kafka-based clinical event streaming
- **Workflow Engine** — BPMN 2.0 clinical pathway orchestration
- **State Machine** — Patient journey state management
- **Notification Service** — Multi-channel alerts (SMS, push, pager, EHR inbox)
- **Task Scheduler** — Clinical task management with priority queuing

### 2. AI Engine (`src/ai/`)
- **Federated Learning Coordinator** — Secure model aggregation across sites
- **CDSS Engine** — Clinical Decision Support with CDS Hooks integration
- **NLP Pipeline** — Clinical text processing (de-identification, NER, relation extraction)
- **Risk Scoring** — Sepsis (qSOFA+), AKI (KDIGO), NEWS2, MEWS, CURB-65
- **Drug Interaction Checker** — Real-time polypharmacy analysis
- **Imaging AI Gateway** — DICOM AI inference orchestration

### 3. Blockchain Layer (`src/blockchain/`)
- **Consent Manager** — Patient consent lifecycle management
- **Audit Ledger** — Immutable PHI access logging
- **Data Provenance** — Full lineage tracking for clinical data
- **Smart Contracts** — Solidity + Chaincode for consent, access, billing
- **ZKP Library** — Zero-knowledge proof generation and verification

### 4. IoT Mesh (`src/iot/`)
- **Device Registry** — Medical device onboarding and lifecycle
- **Protocol Adapters** — MQTT, CoAP, Bluetooth LE, IEEE 11073, HL7 POCT1-A3
- **Stream Processor** — Apache Flink-based real-time vital sign processing
- **Alarm Engine** — Intelligent alarm management (deduplication, escalation)
- **Edge Agent** — Lightweight Go agent for IoT gateways

### 5. Interoperability Engine (`src/interoperability/`)
- **FHIR R5 Server** — Complete HAPI FHIR-based implementation
- **HL7 Translator** — v2.x ↔ FHIR bidirectional transformation
- **DICOM Proxy** — WADO-RS, STOW-RS, QIDO-RS with AI annotation layer
- **Terminology Server** — SNOMED, LOINC, ICD-11, RxNorm with mapping
- **Document Exchange** — XDS.b, MHD, IHE profiles

### 6. Analytics (`src/analytics/`)
- **Population Health Dashboard** — Real-time cohort analysis
- **Quality Metrics** — HEDIS, CQM, Core Measures automated calculation
- **Operational Intelligence** — Bed management, throughput, capacity planning
- **Research Cohort Builder** — Privacy-preserving cohort discovery
- **Custom Report Engine** — Drag-and-drop clinical report builder

### 7. Security (`src/security/`)
- **Identity Provider** — OpenID Connect + SMART on FHIR
- **Access Control** — RBAC + ABAC with clinical role templates
- **Encryption Service** — Key management, field-level encryption
- **Threat Detection** — ML-based anomaly detection on access logs
- **Compliance Engine** — Automated HIPAA, GDPR, ISO 27001 checks

---

## 🔌 API Reference

Full API documentation available at `/api-docs` (Swagger UI) and `/api-docs/redoc`.

### FHIR R5 Endpoints

```
GET    /fhir/R5/Patient/{id}
POST   /fhir/R5/Patient
PUT    /fhir/R5/Patient/{id}
GET    /fhir/R5/Observation?patient={id}&category=vital-signs
POST   /fhir/R5/Bundle          # Transaction bundles
GET    /fhir/R5/metadata        # Capability statement
POST   /fhir/R5/$everything     # Patient everything operation
```

### Clinical AI Endpoints

```
POST   /api/v1/ai/cdss/evaluate          # Evaluate clinical decision
POST   /api/v1/ai/nlp/extract            # Extract from clinical text
GET    /api/v1/ai/risk/{patient_id}      # Get all risk scores
POST   /api/v1/ai/drug-interaction       # Check drug interactions
GET    /api/v1/ai/federated/status       # Federated learning status
POST   /api/v1/ai/imaging/analyze        # Trigger imaging AI
```

### IoT Endpoints

```
POST   /api/v1/iot/devices/register      # Register new device
GET    /api/v1/iot/devices/{id}/vitals   # Stream vital signs (SSE)
POST   /api/v1/iot/vitals/ingest         # Bulk vital ingest
GET    /api/v1/iot/alarms/active         # Active clinical alarms
PUT    /api/v1/iot/alarms/{id}/acknowledge
```

### Blockchain Endpoints

```
POST   /api/v1/consent/grant             # Grant data access consent
DELETE /api/v1/consent/{id}              # Revoke consent
GET    /api/v1/audit/trail/{patient_id}  # Full audit trail
POST   /api/v1/zkp/verify               # Verify ZK proof
GET    /api/v1/provenance/{resource_id}  # Data lineage
```

---

## 🤖 AI & Machine Learning

### Federated Learning Architecture

MedIntelOS implements **FedProx** with differential privacy guarantees:

```python
from medintelos.ai.federated import FederatedCoordinator

coordinator = FederatedCoordinator(
    model_type="sepsis_predictor",
    aggregation="FedProx",
    privacy=DifferentialPrivacy(epsilon=1.0, delta=1e-5),
    min_participants=5,
    rounds=50
)

# Each hospital trains locally, only gradients (with noise) are shared
coordinator.run_federated_round()
```

### Clinical NLP Pipeline

```python
from medintelos.ai.nlp import ClinicalNLPPipeline

pipeline = ClinicalNLPPipeline(
    tasks=["deidentify", "ner", "relation_extraction", "assertion"],
    models={"ner": "medintelos/clinical-bert-ner-v2"}
)

result = pipeline.process(
    text="Patient presents with acute chest pain radiating to left arm. BP 160/90.",
    output_fhir=True  # Returns structured FHIR Observation resources
)
```

### Risk Scoring

```python
from medintelos.ai.risk import RiskEngine

engine = RiskEngine()

scores = engine.calculate_all(patient_id="P12345")
# Returns:
# {
#   "sepsis_qsofa": {"score": 2, "risk": "high", "confidence": 0.87, "explanation": {...}},
#   "aki_kdigo": {"stage": 1, "risk": "moderate", ...},
#   "readmission_30d": {"probability": 0.34, "risk_factors": [...], ...},
#   "deterioration_news2": {"score": 7, "response": "urgent", ...}
# }
```

---

## ⛓️ Blockchain & Audit

### Patient Consent Smart Contract

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract MedIntelOSConsent {
    struct Consent {
        address patient;
        address requester;
        string dataScope;      // FHIR resource types allowed
        string purpose;        // Treatment | Research | Public Health
        uint256 expiresAt;
        bool active;
        string zkProofHash;    // Verification without PHI exposure
    }
    
    mapping(bytes32 => Consent) public consents;
    
    event ConsentGranted(bytes32 indexed consentId, address patient, address requester);
    event ConsentRevoked(bytes32 indexed consentId);
    
    function grantConsent(
        address requester,
        string memory dataScope,
        string memory purpose,
        uint256 duration,
        string memory zkProofHash
    ) external returns (bytes32 consentId) { ... }
    
    function revokeConsent(bytes32 consentId) external { ... }
    function verifyConsent(bytes32 consentId) external view returns (bool) { ... }
}
```

---

## 📡 IoT Integration

### Connecting a Medical Device

```python
from medintelos.iot import DeviceRegistry, VitalStream

# Register device
device = DeviceRegistry.register(
    device_type="patient_monitor",
    manufacturer="Philips",
    model="MX750",
    patient_id="P12345",
    location="ICU-Bed-12",
    protocols=["HL7_POCT1", "MQTT"]
)

# Stream vitals in real-time
stream = VitalStream(device_id=device.id)

@stream.on_vital
def handle_vital(vital: VitalSign):
    # Automatically stored as FHIR Observation
    # Triggers CDSS evaluation
    # Sends alarms if thresholds exceeded
    print(f"HR: {vital.heart_rate} | SpO2: {vital.spo2} | BP: {vital.bp}")

stream.start()
```

---

## 🔐 Security & Compliance

| Standard | Status | Documentation |
|---|---|---|
| HIPAA Security Rule | ✅ Compliant Architecture | [docs/compliance/HIPAA.md](docs/compliance/HIPAA.md) |
| GDPR Article 9 | ✅ Special Category Data Controls | [docs/compliance/GDPR.md](docs/compliance/GDPR.md) |
| ISO 27001 | ✅ Controls Mapped | [docs/compliance/ISO27001.md](docs/compliance/ISO27001.md) |
| ISO 13485 | ✅ QMS Framework Included | [docs/compliance/ISO13485.md](docs/compliance/ISO13485.md) |
| NIST 800-66 | ✅ HIPAA NIST Framework | [docs/compliance/NIST.md](docs/compliance/NIST.md) |
| SOC 2 Type II | ✅ Controls Available | [docs/compliance/SOC2.md](docs/compliance/SOC2.md) |
| IEC 62443 | ✅ Medical IoT Security | [docs/compliance/IEC62443.md](docs/compliance/IEC62443.md) |
| FDA 21 CFR Part 11 | ✅ Electronic Records | [docs/compliance/FDA_21CFR11.md](docs/compliance/FDA_21CFR11.md) |

---

## 🚢 Deployment

### Production Kubernetes Deployment

```bash
# Configure production secrets
kubectl create secret generic medintelos-secrets \
  --from-env-file=configs/.env.production \
  -n medintelos

# Deploy with Helm
helm upgrade --install medintelos ./infrastructure/helm \
  --namespace medintelos \
  --values configs/helm/production-values.yaml \
  --set global.domain=medintelos.yourhospital.org \
  --set global.tls.enabled=true \
  --wait

# Verify deployment
kubectl get pods -n medintelos
./scripts/health-check.sh
```

### Infrastructure as Code

```bash
# Terraform for cloud infrastructure (AWS/GCP/Azure/On-Premise)
cd infrastructure/terraform
terraform init
terraform plan -var-file="production.tfvars"
terraform apply
```

---

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/ -v --cov=src

# Integration tests (requires running services)
pytest tests/integration/ -v

# FHIR conformance tests
./scripts/run-fhir-touchstone.sh

# Security penetration tests
./scripts/run-security-tests.sh

# Load tests (10,000 concurrent patients)
k6 run tests/load/concurrent-patients.js

# Chaos engineering
./scripts/chaos-test.sh --scenario=node-failure
```

---

## 🤝 Contributing

We welcome contributions from clinicians, engineers, researchers, and patients.

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code of Conduct
- Development setup
- Coding standards (clinical safety first)
- Pull request process
- Clinical validation requirements
- How to propose new AI models

**Priority Areas:**
- [ ] Additional language support for clinical NLP (currently: EN, DE, FR, ES, PT)
- [ ] New risk scoring models (validated against public datasets)
- [ ] EHR-specific integration connectors
- [ ] Mobile app improvements
- [ ] Accessibility (WCAG 2.1 AA compliance)

---

## 📖 Research & Publications

MedIntelOS is grounded in peer-reviewed research. The architecture synthesizes innovations from:

- Federated Learning in Healthcare (McMahan et al., Google Brain)
- Differential Privacy for Clinical AI (Dwork & Roth)
- SMART on FHIR (Mandel et al., Harvard)
- Zero-Knowledge Proofs for Health Data (Boneh et al., Stanford)
- Alarm Fatigue Reduction (AAMI Foundation)
- Clinical NLP Benchmarks (BioCreative, n2c2 challenges)

See [research/REFERENCES.md](research/REFERENCES.md) for the full bibliography.

**If you use MedIntelOS in your research, please cite:**
```bibtex
@software{medintelos2024,
  author = {Plesca, Ciprian Stefan},
  title = {MedIntelOS: Medical Intelligence Operating System},
  year = {2024},
  publisher = {GitHub},
  url = {https://github.com/Ciprian-LocalPulse/MedIntelOS},
  license = {MIT}
}
```

---

## 💖 Support & Donations

MedIntelOS is free and open-source forever. If this project helps your hospital, clinic, or research institution, please consider supporting continued development:

### 💳 PayPal
**[paypal.me/agentflowenterprise](https://paypal.me/agentflowenterprise)**

### 🏦 Bank Transfer (EUR / SEPA)
| Field | Value |
|---|---|
| Name | Ciprian Stefan Plesca |
| IBAN | BE83 9679 1975 8915 |
| BIC/SWIFT | TRWIBEB1XXX |
| Bank | Wise, Rue du Trône 100, Brussels, Belgium |

### 🏦 Bank Transfer (GBP)
| Field | Value |
|---|---|
| Name | Ciprian Stefan Plesca |
| Account Number | 92055372 |
| Sort Code | 23-14-70 |
| IBAN | GB68 TRWI 2314 7092 0553 72 |
| BIC/SWIFT | TRWIGB2LXXX |

### 🏦 Bank Transfer (USD)
| Field | Value |
|---|---|
| Name | Ciprian Stefan Plesca |
| Account Type | Checking |
| Routing Number | 026073150 |
| Account Number | 8314225367 |
| BIC/SWIFT | CMFGUS33 |
| Bank | Community Federal Savings Bank, 89-16 Jamaica Ave, Woodhaven, NY 11421, USA |

### ₿ Cryptocurrency
| Currency | Address |
|---|---|
| **Bitcoin (BTC)** | `bc1qf3yy0w8z37rwavxpu38wem3yffpanw7wzj32qj` |
| **Ethereum (ETH)** | `0x27d9a6a5b8507e6031bb044319410da96222d402` |

Every contribution — no matter how small — directly funds:
- New AI model development and clinical validation
- Security audits and penetration testing
- Documentation and clinical training materials
- Hospital pilot deployments in underserved regions

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for full text.

**Medical Disclaimer:** MedIntelOS is a software platform and does not constitute medical advice. Clinical decisions must always involve qualified healthcare professionals. AI outputs are decision support tools only and must not replace clinical judgment.

---

<div align="center">

**Built with ❤️ for doctors, nurses, and patients worldwide**

*"Technology should heal, not complicate."*

[Website](https://github.com/Ciprian-LocalPulse/MedIntelOS) · [Docs](docs/) · [Issues](https://github.com/Ciprian-LocalPulse/MedIntelOS/issues) · [Discussions](https://github.com/Ciprian-LocalPulse/MedIntelOS/discussions)

</div>
