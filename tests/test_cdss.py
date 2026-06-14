from medintelos.cdss import CDSSEngine, LabResult, PatientContext, RiskLevel, RiskScorer, VitalSigns


def test_qsofa_high_risk_generates_card() -> None:
    context = PatientContext(
        patient_id="synthetic-1",
        vitals=VitalSigns(systolic_bp=90, respiratory_rate=24, gcs=14, spo2=93),
    )

    response = CDSSEngine().evaluate(context)

    assert response["cards"]
    assert response["_medintelos"]["risk_scores"][0]["risk_level"] in {"high", "critical"}


def test_zero_threshold_is_not_treated_as_missing() -> None:
    lab = LabResult(
        loinc_code="example",
        display_name="Example",
        value=-1,
        unit="u",
        reference_low=0,
        critical_low=0,
    )

    assert lab.is_abnormal is True
    assert lab.is_critical is True


def test_news2_low_risk_for_normal_vitals() -> None:
    score = RiskScorer.news2(
        VitalSigns(
            heart_rate=75,
            systolic_bp=120,
            respiratory_rate=16,
            temperature=37,
            spo2=98,
            gcs=15,
        )
    )

    assert score.risk_level == RiskLevel.LOW
