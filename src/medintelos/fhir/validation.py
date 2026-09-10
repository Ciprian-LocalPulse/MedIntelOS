"""MedIntelOS's own FHIR resource validation, exposed via the `$validate`
operation (see api/app.py).

**What this is not:** a claim of conformance to US Core or the
International Patient Summary (IPS). Neither implementation guide has a
published FHIR R5 version as of this writing — both are R4-based — and
MedIntelOS is R5. Adapting their R4 profiles to R5 resources would produce
validation that looks authoritative but isn't; that's worse than no
validation, so this module does not attempt it.

**What this is:** required-element (cardinality >= 1) checks taken directly
from the FHIR R5 base specification, for the resource types MedIntelOS's
own builders (`fhir/builders.py`) actually construct — Patient, Observation,
Condition, MedicationRequest. Other resource types get only the generic
checks. This module does not implement FHIRPath invariants (e.g. the
`con-3`/`con-4`-style constraints FHIR profiles typically carry), value-set
bindings beyond the small local LOINC table in `terminology.py`, or full
structural (data-type-level) validation. A real conformance-testing need
should use the official HL7 FHIR validator or a terminology-server-backed
validator, not this module.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from medintelos.fhir.terminology import LOINC_SYSTEM, known_vital_sign_code

Severity = str  # "error" | "warning" | "information"


class ValidationIssue:
    __slots__ = ("severity", "code", "diagnostics", "expression")

    def __init__(
        self, severity: Severity, code: str, diagnostics: str, expression: str | None = None
    ) -> None:
        self.severity = severity
        self.code = code
        self.diagnostics = diagnostics
        self.expression = expression

    def to_dict(self) -> dict[str, Any]:
        issue: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "diagnostics": self.diagnostics,
        }
        if self.expression:
            issue["expression"] = [self.expression]
        return issue


# Required (cardinality 1..1 or 1..*) top-level elements per the FHIR R5
# base specification, for the resource types MedIntelOS actually builds.
# Deliberately not a full copy of every required element on every resource
# in the spec — see module docstring for scope.
_REQUIRED_ELEMENTS: dict[str, list[str]] = {
    "Observation": ["status", "code"],
    "Condition": ["subject"],
    "MedicationRequest": ["status", "intent", "subject"],
    # Patient has no required top-level elements in the base spec; nothing
    # to check here beyond the generic resourceType check every resource
    # gets.
}


def validate_resource(resource_type: str, resource: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    declared_type = resource.get("resourceType")
    if declared_type != resource_type:
        issues.append(
            ValidationIssue(
                "error",
                "invalid",
                f"resourceType {declared_type!r} does not match {resource_type!r}",
                expression="resourceType",
            )
        )

    for element in _REQUIRED_ELEMENTS.get(resource_type, []):
        if element not in resource or resource[element] in (None, "", [], {}):
            issues.append(
                ValidationIssue(
                    "error",
                    "required",
                    f"{resource_type}.{element} is required",
                    expression=element,
                )
            )

    if resource_type == "Observation":
        issues.extend(_check_vital_signs_terminology(resource))

    if not issues:
        issues.append(
            ValidationIssue(
                "information",
                "informational",
                (
                    f"No structural issues found by MedIntelOS's own {resource_type} checks. "
                    "This is not a claim of US Core or IPS conformance — see "
                    "fhir/validation.py's module docstring."
                ),
            )
        )

    return issues


def _check_vital_signs_terminology(observation: dict[str, Any]) -> list[ValidationIssue]:
    categories = observation.get("category", [])
    is_vital_signs = any(
        coding.get("code") == "vital-signs"
        for category in categories
        for coding in category.get("coding", [])
    )
    if not is_vital_signs:
        return []

    issues: list[ValidationIssue] = []
    codings = observation.get("code", {}).get("coding", [])
    # A blood-pressure panel carries its LOINC codes on `component`, not on
    # the top-level `code` — check both so the panel form is covered too.
    component_codings = [
        coding
        for component in observation.get("component", [])
        for coding in component.get("code", {}).get("coding", [])
    ]
    for coding in codings + component_codings:
        system = coding.get("system")
        code = coding.get("code")
        if system != LOINC_SYSTEM or not code:
            continue
        if known_vital_sign_code(system, code) is None:
            issues.append(
                ValidationIssue(
                    "warning",
                    "code-invalid",
                    (
                        f"LOINC code {code!r} is not in MedIntelOS's small local "
                        "vital-signs table (fhir/terminology.py). This does not mean "
                        "the code is wrong — only that this reference implementation "
                        "doesn't recognize it — so it's a warning, not an error."
                    ),
                    expression="code",
                )
            )
    return issues


def build_operation_outcome(issues: list[ValidationIssue]) -> dict[str, Any]:
    return {
        "resourceType": "OperationOutcome",
        "id": str(uuid4()),
        "issue": [issue.to_dict() for issue in issues],
    }


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)
