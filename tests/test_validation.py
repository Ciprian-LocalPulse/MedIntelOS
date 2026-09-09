from __future__ import annotations

from medintelos.fhir.validation import build_operation_outcome, has_errors, validate_resource


def test_valid_observation_has_no_errors():
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
        "subject": {"reference": "Patient/1"},
    }
    issues = validate_resource("Observation", observation)
    assert not has_errors(issues)


def test_observation_missing_status_is_an_error():
    observation = {
        "resourceType": "Observation",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
    }
    issues = validate_resource("Observation", observation)
    assert has_errors(issues)
    assert any(issue.code == "required" and "status" in issue.diagnostics for issue in issues)


def test_observation_missing_code_is_an_error():
    observation = {"resourceType": "Observation", "status": "final"}
    issues = validate_resource("Observation", observation)
    assert has_errors(issues)
    assert any(issue.expression == "code" for issue in issues)


def test_condition_requires_subject():
    issues = validate_resource("Condition", {"resourceType": "Condition"})
    assert has_errors(issues)
    assert any(issue.expression == "subject" for issue in issues)


def test_medication_request_requires_status_intent_subject():
    issues = validate_resource("MedicationRequest", {"resourceType": "MedicationRequest"})
    missing = {issue.expression for issue in issues if issue.code == "required"}
    assert missing == {"status", "intent", "subject"}


def test_patient_has_no_required_elements():
    issues = validate_resource("Patient", {"resourceType": "Patient"})
    assert not has_errors(issues)


def test_resource_type_mismatch_is_an_error():
    issues = validate_resource("Patient", {"resourceType": "Observation"})
    assert has_errors(issues)
    assert any(issue.code == "invalid" for issue in issues)


def test_unknown_vital_sign_loinc_code_is_a_warning_not_an_error():
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                    }
                ]
            }
        ],
        "code": {"coding": [{"system": "http://loinc.org", "code": "99999-9"}]},
        "subject": {"reference": "Patient/1"},
    }
    issues = validate_resource("Observation", observation)
    assert not has_errors(issues)
    assert any(issue.severity == "warning" and issue.code == "code-invalid" for issue in issues)


def test_known_vital_sign_loinc_code_produces_no_warning():
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                    }
                ]
            }
        ],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
        "subject": {"reference": "Patient/1"},
    }
    issues = validate_resource("Observation", observation)
    assert not any(issue.code == "code-invalid" for issue in issues)


def test_blood_pressure_panel_components_are_checked():
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                    }
                ]
            }
        ],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9"}]},
        "component": [
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]}},
            {"code": {"coding": [{"system": "http://loinc.org", "code": "not-a-real-code"}]}},
        ],
    }
    issues = validate_resource("Observation", observation)
    warnings = [issue for issue in issues if issue.code == "code-invalid"]
    assert len(warnings) == 1


def test_non_vital_signs_observation_skips_terminology_check():
    observation = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "totally-made-up"}]},
    }
    issues = validate_resource("Observation", observation)
    assert not any(issue.code == "code-invalid" for issue in issues)


def test_no_issues_yields_an_informational_message():
    issues = validate_resource("Patient", {"resourceType": "Patient"})
    assert len(issues) == 1
    assert issues[0].severity == "information"


def test_operation_outcome_shape():
    issues = validate_resource("Condition", {"resourceType": "Condition"})
    outcome = build_operation_outcome(issues)
    assert outcome["resourceType"] == "OperationOutcome"
    assert outcome["issue"][0]["severity"] == "error"
    assert outcome["issue"][0]["expression"] == ["subject"]
