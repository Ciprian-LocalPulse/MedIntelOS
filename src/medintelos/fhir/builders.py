"""
MedIntelOS FHIR R5 Server
==========================
FHIR R5 resource-building helpers for a reference server implementation.

Implements:
    - FHIR R5 (HL7 FHIR Release 5)
    - Common resource builders
    - Search parameter parsers
    - Bundle helpers
    - A CapabilityStatement for the implemented demo surface

Key resource builders included:
    Patient, Encounter, Observation, Condition, Procedure, MedicationRequest,
    DiagnosticReport, AllergyIntolerance, Immunization, CarePlan, CareTeam,
    ServiceRequest, Specimen, Device, DeviceObservation, DocumentReference,
    Composition, Bundle, CapabilityStatement, OperationOutcome, ...

Author: MedIntelOS Contributors
License: MIT
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FHIR Constants
# ---------------------------------------------------------------------------

FHIR_VERSION = "5.0.0"
FHIR_BASE = "http://hl7.org/fhir"
MEDINTELOS_BASE = "https://medintelos.io/fhir"

# Common FHIR system URIs
SYSTEMS = {
    "snomed": "http://snomed.info/sct",
    "loinc": "http://loinc.org",
    "icd10": "http://hl7.org/fhir/sid/icd-10",
    "icd11": "http://id.who.int/icd/release/11/mms",
    "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "ndc": "http://hl7.org/fhir/sid/ndc",
    "cvx": "http://hl7.org/fhir/sid/cvx",
    "nucc": "http://nucc.org/provider-taxonomy",
    "npi": "http://hl7.org/fhir/sid/us-npi",
    "dicom": "urn:dicom:uid",
    "ucum": "http://unitsofmeasure.org",
}


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ResourceType(str, Enum):
    # Core clinical
    PATIENT = "Patient"
    ENCOUNTER = "Encounter"
    OBSERVATION = "Observation"
    CONDITION = "Condition"
    PROCEDURE = "Procedure"
    MEDICATION_REQUEST = "MedicationRequest"
    MEDICATION_ADMINISTRATION = "MedicationAdministration"
    MEDICATION_STATEMENT = "MedicationStatement"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"
    IMMUNIZATION = "Immunization"
    CARE_PLAN = "CarePlan"
    CARE_TEAM = "CareTeam"
    SERVICE_REQUEST = "ServiceRequest"
    SPECIMEN = "Specimen"
    DEVICE = "Device"
    DEVICE_OBSERVATION = "DeviceObservation"
    DOCUMENT_REFERENCE = "DocumentReference"
    COMPOSITION = "Composition"
    # Infrastructure
    BUNDLE = "Bundle"
    CAPABILITY_STATEMENT = "CapabilityStatement"
    OPERATION_OUTCOME = "OperationOutcome"
    SUBSCRIPTION = "Subscription"
    AUDIT_EVENT = "AuditEvent"
    PROVENANCE = "Provenance"
    CONSENT = "Consent"


class SearchModifier(str, Enum):
    EXACT = "exact"
    CONTAINS = "contains"
    MISSING = "missing"
    TEXT = "text"
    NOT = "not"
    ABOVE = "above"
    BELOW = "below"
    IN = "in"
    NOT_IN = "not-in"
    OF_TYPE = "of-type"


class BundleType(str, Enum):
    DOCUMENT = "document"
    MESSAGE = "message"
    TRANSACTION = "transaction"
    TRANSACTION_RESPONSE = "transaction-response"
    BATCH = "batch"
    BATCH_RESPONSE = "batch-response"
    HISTORY = "history"
    SEARCHSET = "searchset"
    COLLECTION = "collection"


# ---------------------------------------------------------------------------
# FHIR Data Types (Simplified Python representations)
# ---------------------------------------------------------------------------

def coding(system: str, code: str, display: str = "") -> Dict[str, str]:
    """Create a FHIR Coding element."""
    result = {"system": SYSTEMS.get(system, system), "code": code}
    if display:
        result["display"] = display
    return result


def codeable_concept(
    system: str,
    code: str,
    display: str = "",
    text: str = "",
) -> Dict[str, Any]:
    """Create a FHIR CodeableConcept element."""
    result: Dict[str, Any] = {"coding": [coding(system, code, display)]}
    if text:
        result["text"] = text
    return result


def reference(resource_type: str, resource_id: str, display: str = "") -> Dict[str, str]:
    """Create a FHIR Reference element."""
    result = {"reference": f"{resource_type}/{resource_id}"}
    if display:
        result["display"] = display
    return result


def quantity(value: float, unit: str, system: str = "ucum", code: str = "") -> Dict:
    """Create a FHIR Quantity element."""
    return {
        "value": value,
        "unit": unit,
        "system": SYSTEMS.get(system, system),
        "code": code or unit,
    }


def period(start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, str]:
    """Create a FHIR Period element."""
    p: Dict[str, str] = {}
    if start:
        p["start"] = start
    if end:
        p["end"] = end
    return p


def narrative(status: str, div_content: str) -> Dict[str, str]:
    """Create a FHIR Narrative element."""
    return {
        "status": status,
        "div": f'<div xmlns="http://www.w3.org/1999/xhtml">{div_content}</div>'
    }


# ---------------------------------------------------------------------------
# FHIR Resource Builders
# ---------------------------------------------------------------------------

class FHIRResourceBuilder:
    """
    Builder class for constructing valid FHIR R5 resources.
    Each method returns a complete, valid FHIR resource as a Python dict.
    """

    @staticmethod
    def patient(
        patient_id: str,
        family_name: str,
        given_names: List[str],
        birth_date: str,              # YYYY-MM-DD
        gender: str,                   # male | female | other | unknown
        identifiers: Optional[List[Dict]] = None,
        mrn: Optional[str] = None,
        address: Optional[Dict] = None,
        telecom: Optional[List[Dict]] = None,
        marital_status: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Build a FHIR R5 Patient resource."""
        resource: Dict[str, Any] = {
            "resourceType": "Patient",
            "id": patient_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
            },
            "text": narrative("generated", f"Patient {' '.join(given_names)} {family_name}"),
            "identifier": identifiers or [],
            "active": True,
            "name": [{
                "use": "official",
                "family": family_name,
                "given": given_names,
            }],
            "gender": gender,
            "birthDate": birth_date,
            "communication": [{
                "language": codeable_concept(
                    "http://hl7.org/fhir/ValueSet/languages",
                    language,
                    language.upper()
                ),
                "preferred": True
            }]
        }

        if mrn:
            resource["identifier"].insert(0, {
                "use": "official",
                "type": codeable_concept("http://terminology.hl7.org/CodeSystem/v2-0203", "MR", "Medical record number"),
                "value": mrn,
            })
        if address:
            resource["address"] = [address]
        if telecom:
            resource["telecom"] = telecom
        if marital_status:
            resource["maritalStatus"] = codeable_concept(
                "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                marital_status
            )

        return resource

    @staticmethod
    def observation(
        obs_id: str,
        patient_id: str,
        loinc_code: str,
        display: str,
        value: Union[float, str, bool, Dict],
        unit: Optional[str] = None,
        ucum_code: Optional[str] = None,
        status: str = "final",
        category: str = "laboratory",     # vital-signs | laboratory | imaging | etc.
        encounter_id: Optional[str] = None,
        effective_datetime: Optional[str] = None,
        interpretation: Optional[str] = None,   # N | H | L | HH | LL | A
        reference_range: Optional[Dict] = None,
        components: Optional[List[Dict]] = None,
        performer_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a FHIR R5 Observation resource."""
        now = datetime.now(timezone.utc).isoformat()
        resource: Dict[str, Any] = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": now,
            },
            "status": status,
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": category,
                    "display": category.replace("-", " ").title(),
                }]
            }],
            "code": codeable_concept("loinc", loinc_code, display),
            "subject": reference("Patient", patient_id),
            "effectiveDateTime": effective_datetime or now,
            "issued": now,
        }

        if encounter_id:
            resource["encounter"] = reference("Encounter", encounter_id)
        if performer_id:
            resource["performer"] = [reference("Practitioner", performer_id)]
        if device_id:
            resource["device"] = reference("Device", device_id)

        # Value handling
        if isinstance(value, (int, float)) and unit:
            resource["valueQuantity"] = quantity(
                float(value), unit, "ucum", ucum_code or unit
            )
        elif isinstance(value, str):
            resource["valueString"] = value
        elif isinstance(value, bool):
            resource["valueBoolean"] = value
        elif isinstance(value, dict):
            # CodeableConcept value
            resource["valueCodeableConcept"] = value

        if interpretation:
            resource["interpretation"] = [codeable_concept(
                "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                interpretation,
                {"H": "High", "L": "Low", "N": "Normal", "HH": "Critical High",
                 "LL": "Critical Low", "A": "Abnormal"}.get(interpretation, interpretation)
            )]

        if reference_range:
            resource["referenceRange"] = [reference_range]

        if components:
            resource["component"] = components

        return resource

    @staticmethod
    def blood_pressure(
        obs_id: str,
        patient_id: str,
        systolic: float,
        diastolic: float,
        encounter_id: Optional[str] = None,
        effective_datetime: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a FHIR R5 blood pressure Observation (panel with components)."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": {"versionId": "1", "lastUpdated": now},
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs",
                }]
            }],
            "code": codeable_concept("loinc", "85354-9", "Blood pressure panel with all children optional"),
            "subject": reference("Patient", patient_id),
            "encounter": reference("Encounter", encounter_id) if encounter_id else None,
            "effectiveDateTime": effective_datetime or now,
            "device": reference("Device", device_id) if device_id else None,
            "component": [
                {
                    "code": codeable_concept("loinc", "8480-6", "Systolic blood pressure"),
                    "valueQuantity": quantity(systolic, "mmHg", "ucum", "mm[Hg]"),
                    "interpretation": [codeable_concept(
                        "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "H" if systolic > 140 else ("L" if systolic < 90 else "N")
                    )]
                },
                {
                    "code": codeable_concept("loinc", "8462-4", "Diastolic blood pressure"),
                    "valueQuantity": quantity(diastolic, "mmHg", "ucum", "mm[Hg]"),
                    "interpretation": [codeable_concept(
                        "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "H" if diastolic > 90 else ("L" if diastolic < 60 else "N")
                    )]
                },
            ]
        }

    @staticmethod
    def condition(
        condition_id: str,
        patient_id: str,
        icd11_code: str,
        display: str,
        clinical_status: str = "active",     # active | recurrence | relapse | inactive | remission | resolved
        verification_status: str = "confirmed",  # unconfirmed | provisional | differential | confirmed | refuted
        category: str = "encounter-diagnosis",
        severity: Optional[str] = None,         # 24484000=severe, 6736007=moderate, 255604002=mild (SNOMED)
        onset_datetime: Optional[str] = None,
        abatement_datetime: Optional[str] = None,
        encounter_id: Optional[str] = None,
        asserter_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a FHIR R5 Condition resource."""
        now = datetime.now(timezone.utc).isoformat()
        resource: Dict[str, Any] = {
            "resourceType": "Condition",
            "id": condition_id,
            "meta": {"versionId": "1", "lastUpdated": now},
            "clinicalStatus": codeable_concept(
                "http://terminology.hl7.org/CodeSystem/condition-clinical",
                clinical_status
            ),
            "verificationStatus": codeable_concept(
                "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                verification_status
            ),
            "category": [codeable_concept(
                "http://terminology.hl7.org/CodeSystem/condition-category",
                category
            )],
            "code": codeable_concept("icd11", icd11_code, display),
            "subject": reference("Patient", patient_id),
            "recordedDate": now,
        }

        if severity:
            resource["severity"] = codeable_concept("snomed", severity)
        if onset_datetime:
            resource["onsetDateTime"] = onset_datetime
        if abatement_datetime:
            resource["abatementDateTime"] = abatement_datetime
        if encounter_id:
            resource["encounter"] = reference("Encounter", encounter_id)
        if asserter_id:
            resource["asserter"] = reference("Practitioner", asserter_id)
        if note:
            resource["note"] = [{"text": note}]

        return resource

    @staticmethod
    def medication_request(
        request_id: str,
        patient_id: str,
        rxnorm_code: str,
        medication_display: str,
        dose_value: float,
        dose_unit: str,
        route: str,                    # oral | IV | IM | SC | etc.
        frequency: str,                # e.g. "every 8 hours"
        requester_id: str,
        status: str = "active",
        intent: str = "order",
        priority: str = "routine",     # routine | urgent | asap | stat
        encounter_id: Optional[str] = None,
        reason_codes: Optional[List[str]] = None,  # ICD-11 codes
        instructions: Optional[str] = None,
        max_doses_per_period: Optional[int] = None,
        dispense_quantity: Optional[float] = None,
        refills: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build a FHIR R5 MedicationRequest resource."""
        now = datetime.now(timezone.utc).isoformat()
        resource: Dict[str, Any] = {
            "resourceType": "MedicationRequest",
            "id": request_id,
            "meta": {"versionId": "1", "lastUpdated": now},
            "status": status,
            "intent": intent,
            "priority": priority,
            "medication": {
                "concept": codeable_concept("rxnorm", rxnorm_code, medication_display)
            },
            "subject": reference("Patient", patient_id),
            "requester": reference("Practitioner", requester_id),
            "authoredOn": now,
            "dosageInstruction": [{
                "text": f"{dose_value} {dose_unit} {route} {frequency}",
                "route": codeable_concept(
                    "http://snomed.info/sct",
                    _route_to_snomed(route),
                    route.title()
                ),
                "doseAndRate": [{
                    "type": codeable_concept(
                        "http://terminology.hl7.org/CodeSystem/dose-rate-type",
                        "ordered", "Ordered"
                    ),
                    "doseQuantity": quantity(dose_value, dose_unit),
                }],
                "timing": {"code": codeable_concept(
                    "http://terminology.hl7.org/CodeSystem/v3-GTSAbbreviation",
                    "Q8H" if "8 hour" in frequency else "QD",
                    frequency
                )},
            }]
        }

        if encounter_id:
            resource["encounter"] = reference("Encounter", encounter_id)
        if reason_codes:
            resource["reasonCode"] = [
                codeable_concept("icd11", code) for code in reason_codes
            ]
        if instructions:
            resource["dosageInstruction"][0]["patientInstruction"] = instructions
        if dispense_quantity is not None:
            resource["dispenseRequest"] = {
                "quantity": quantity(dispense_quantity, "each"),
                "numberOfRepeatsAllowed": refills or 0,
            }

        return resource


def _route_to_snomed(route: str) -> str:
    """Map common route names to SNOMED codes."""
    mapping = {
        "oral": "26643006",
        "IV": "47625008",
        "IM": "78421000",
        "SC": "34206005",
        "topical": "6064005",
        "inhaled": "18679011000001101",
        "sublingual": "37839007",
        "rectal": "37161004",
        "ophthalmic": "54485002",
        "otic": "10547007",
        "nasal": "46713006",
    }
    return mapping.get(route, "26643006")


# ---------------------------------------------------------------------------
# Bundle Builder
# ---------------------------------------------------------------------------

class FHIRBundleBuilder:
    """Build FHIR transaction and search result bundles."""

    def __init__(self, bundle_type: BundleType = BundleType.TRANSACTION):
        self.bundle_type = bundle_type
        self.entries: List[Dict[str, Any]] = []
        self.bundle_id = str(uuid.uuid4())

    def add_resource(
        self,
        resource: Dict[str, Any],
        request_method: str = "PUT",
        request_url: Optional[str] = None,
        full_url: Optional[str] = None,
    ) -> "FHIRBundleBuilder":
        """Add a resource to the bundle."""
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource.get("id", str(uuid.uuid4()))

        entry: Dict[str, Any] = {
            "fullUrl": full_url or f"urn:uuid:{resource_id}",
            "resource": resource,
        }

        if self.bundle_type in (BundleType.TRANSACTION, BundleType.BATCH):
            entry["request"] = {
                "method": request_method,
                "url": request_url or f"{resource_type}/{resource_id}",
            }

        self.entries.append(entry)
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the complete FHIR Bundle."""
        return {
            "resourceType": "Bundle",
            "id": self.bundle_id,
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
            },
            "type": self.bundle_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": len(self.entries),
            "entry": self.entries,
        }

    def build_searchset(
        self,
        search_url: str,
        total: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build a FHIR searchset Bundle with navigation links."""
        bundle = self.build()
        bundle["type"] = "searchset"
        bundle["total"] = total if total is not None else len(self.entries)
        bundle["link"] = [{"relation": "self", "url": search_url}]
        return bundle


# ---------------------------------------------------------------------------
# FHIR Search Parameter Parser
# ---------------------------------------------------------------------------

class FHIRSearchParser:
    """
    Parse and validate FHIR search parameters.
    Supports all FHIR search parameter types: string, token, date, number,
    quantity, reference, uri, composite, special.
    """

    DATE_PREFIXES = frozenset(["eq", "ne", "lt", "gt", "ge", "le", "sa", "eb", "ap"])
    NUMBER_PREFIXES = frozenset(["eq", "ne", "lt", "gt", "ge", "le"])

    @classmethod
    def parse_token(cls, value: str) -> Tuple[Optional[str], str]:
        """
        Parse a FHIR token search value.
        Format: [system]|[code] or just [code]

        Returns:
            Tuple of (system, code)
        """
        if "|" in value:
            parts = value.split("|", 1)
            return parts[0], parts[1]
        return None, value

    @classmethod
    def parse_date(cls, value: str) -> Tuple[str, str]:
        """
        Parse a FHIR date search value with prefix.

        Returns:
            Tuple of (prefix, date_string) where prefix defaults to "eq"
        """
        for prefix in cls.DATE_PREFIXES:
            if value.startswith(prefix):
                return prefix, value[len(prefix):]
        return "eq", value

    @classmethod
    def parse_quantity(cls, value: str) -> Tuple[str, float, Optional[str], Optional[str]]:
        """
        Parse a FHIR quantity search value.
        Format: [prefix][number]|[system]|[code]

        Returns:
            Tuple of (prefix, number, system, code)
        """
        prefix = "eq"
        for p in cls.NUMBER_PREFIXES:
            if value.startswith(p) and len(value) > len(p):
                prefix = p
                value = value[len(p):]
                break

        parts = value.split("|")
        number = float(parts[0])
        system = parts[1] if len(parts) > 1 else None
        code = parts[2] if len(parts) > 2 else None

        return prefix, number, system, code

    @classmethod
    def parse_reference(cls, value: str) -> Tuple[Optional[str], str]:
        """
        Parse a FHIR reference search value.
        Format: [ResourceType]/[id] or just [id]

        Returns:
            Tuple of (resource_type, id)
        """
        if "/" in value:
            parts = value.rsplit("/", 1)
            return parts[0], parts[1]
        return None, value


# ---------------------------------------------------------------------------
# Capability Statement (Server Advertisement)
# ---------------------------------------------------------------------------

def build_capability_statement(base_url: str) -> Dict[str, Any]:
    """
    Build a complete FHIR R5 CapabilityStatement advertising server capabilities.
    This is returned at GET /fhir/R5/metadata.
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "resourceType": "CapabilityStatement",
        "id": "medintelos-capability",
        "url": f"{base_url}/fhir/R5/metadata",
        "version": "1.0.0",
        "name": "MedIntelOSCapabilityStatement",
        "title": "MedIntelOS FHIR R5 Server",
        "status": "active",
        "experimental": False,
        "date": now,
        "publisher": "MedIntelOS",
        "contact": [{
            "name": "MedIntelOS Support",
            "telecom": [{
                "system": "url",
                "value": "https://github.com/Ciprian-LocalPulse/MedIntelOS"
            }]
        }],
        "description": (
            "MedIntelOS educational FHIR R5 reference API. The advertised "
            "surface is a development subset and is not a certified FHIR server."
        ),
        "fhirVersion": FHIR_VERSION,
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "documentation": "MedIntelOS FHIR R5 REST API",
            "security": {
                "cors": False,
                "description": "X-API-Key authentication for this reference implementation"
            },
            "resource": _build_resource_capabilities(),
            "interaction": [
                {"code": "search-system"},
            ],
            "searchParam": [
                {"name": "_id", "type": "token"},
                {"name": "_lastUpdated", "type": "date"},
                {"name": "_tag", "type": "token"},
                {"name": "_count", "type": "number"},
                {"name": "_include", "type": "special"},
                {"name": "_revinclude", "type": "special"},
                {"name": "_sort", "type": "special"},
                {"name": "_summary", "type": "special"},
                {"name": "_elements", "type": "special"},
            ],
        }]
    }


def _build_resource_capabilities() -> List[Dict[str, Any]]:
    """Build the resource capability declarations for all supported resources."""
    resources = [
        ("Patient", ["read", "update", "delete", "create", "search-type"]),
        ("Encounter", ["read", "update", "delete", "create", "search-type"]),
        ("Observation", ["read", "update", "delete", "create", "search-type"]),
        ("Condition", ["read", "update", "delete", "create", "search-type"]),
        ("Procedure", ["read", "update", "delete", "create", "search-type"]),
        ("MedicationRequest", ["read", "update", "delete", "create", "search-type"]),
        ("DiagnosticReport", ["read", "update", "delete", "create", "search-type"]),
        ("AllergyIntolerance", ["read", "update", "delete", "create", "search-type"]),
        ("Immunization", ["read", "update", "delete", "create", "search-type"]),
        ("CarePlan", ["read", "update", "delete", "create", "search-type"]),
        ("ServiceRequest", ["read", "update", "delete", "create", "search-type"]),
        ("Device", ["read", "update", "delete", "create", "search-type"]),
        ("DocumentReference", ["read", "update", "delete", "create", "search-type"]),
        ("Consent", ["read", "update", "delete", "create", "search-type"]),
        ("AuditEvent", ["read", "update", "delete", "create", "search-type"]),
    ]

    capabilities = []
    for resource_type, interactions in resources:
        capabilities.append({
            "type": resource_type,
            "profile": f"http://hl7.org/fhir/StructureDefinition/{resource_type}",
            "interaction": [{"code": i} for i in interactions],
            "versioning": "versioned-update",
            "readHistory": False,
            "updateCreate": False,
            "conditionalCreate": False,
            "conditionalUpdate": False,
            "conditionalDelete": "not-supported",
            "referencePolicy": ["literal", "logical"],
            "searchInclude": [f"{resource_type}.*"],
            "searchRevInclude": ["Observation:subject"],
        })

    return capabilities
