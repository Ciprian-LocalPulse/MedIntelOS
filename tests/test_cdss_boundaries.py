"""Boundary-value tests for RiskScorer's clinical rules.

Every threshold in qsofa/news2/aki_kdigo/cha2ds2_vasc is tested at the
boundary (last value on one side, first value on the other), plus the
missing-data path (None) and, where clinically meaningful, the value-of-zero
path. Several tests here are regressions for real defects found while
writing this suite:

- NEWS2 heart rate 41-50 bpm was scoring 1 point instead of the published
  chart's 2 points.
- A measured vital of exactly 0 (e.g. respiratory_rate=0, apnea) was being
  silently treated the same as "not measured" due to truthy checks instead
  of `is not None` checks.
- AKI KDIGO's absolute creatinine >=4.0 mg/dL stage-3 criterion only fired
  when a baseline creatinine was also available, missing severe AKI at
  initial presentation with no prior labs.

See CHANGELOG.md for the fixes.
"""

from __future__ import annotations

import pytest

from medintelos.cdss import RiskLevel, RiskScorer, VitalSigns

# ---------------------------------------------------------------------------
# qSOFA
# ---------------------------------------------------------------------------


class DummyContext:
    pass


def test_qsofa_all_missing_scores_zero():
    score = RiskScorer.qsofa(VitalSigns(), DummyContext())
    assert score.score_value == 0
    assert score.risk_level == RiskLevel.LOW


@pytest.mark.parametrize(
    "rr,expected_points",
    [(21, 0), (22, 1), (23, 1)],
)
def test_qsofa_respiratory_rate_boundary(rr, expected_points):
    score = RiskScorer.qsofa(VitalSigns(respiratory_rate=rr), DummyContext())
    assert score.score_value == expected_points


@pytest.mark.parametrize("gcs,expected_points", [(15, 0), (14, 1)])
def test_qsofa_gcs_boundary(gcs, expected_points):
    score = RiskScorer.qsofa(VitalSigns(gcs=gcs), DummyContext())
    assert score.score_value == expected_points


@pytest.mark.parametrize("sbp,expected_points", [(101, 0), (100, 1)])
def test_qsofa_systolic_bp_boundary(sbp, expected_points):
    score = RiskScorer.qsofa(VitalSigns(systolic_bp=sbp), DummyContext())
    assert score.score_value == expected_points


def test_qsofa_systolic_bp_zero_is_not_treated_as_missing():
    # A measured SBP of 0 is an extreme (if implausible) real value, not
    # "not measured" -- must still be scored, not silently skipped.
    score = RiskScorer.qsofa(VitalSigns(systolic_bp=0), DummyContext())
    assert score.explanation.get("systolic_bp_le_100") == 1.0


def test_qsofa_score_of_2_is_high_risk():
    score = RiskScorer.qsofa(
        VitalSigns(respiratory_rate=22, systolic_bp=100), DummyContext()
    )
    assert score.score_value == 2
    assert score.risk_level == RiskLevel.HIGH


def test_qsofa_all_three_criteria_caps_at_3():
    score = RiskScorer.qsofa(
        VitalSigns(respiratory_rate=30, gcs=10, systolic_bp=80), DummyContext()
    )
    assert score.score_value == 3


# ---------------------------------------------------------------------------
# NEWS2
# ---------------------------------------------------------------------------


def test_news2_all_missing_scores_zero():
    score = RiskScorer.news2(VitalSigns())
    assert score.score_value == 0
    assert score.risk_level == RiskLevel.LOW


@pytest.mark.parametrize(
    "rr,expected_points",
    [(8, 3), (9, 1), (11, 1), (12, 0), (20, 0), (21, 2), (24, 2), (25, 3)],
)
def test_news2_respiratory_rate_boundaries(rr, expected_points):
    score = RiskScorer.news2(VitalSigns(respiratory_rate=rr))
    assert score.explanation["respiratory_rate"] == expected_points


def test_news2_respiratory_rate_zero_scores_maximum_not_skipped():
    # Apnea (RR=0) is the most dangerous possible reading, not "no data".
    score = RiskScorer.news2(VitalSigns(respiratory_rate=0))
    assert score.explanation["respiratory_rate"] == 3.0


@pytest.mark.parametrize(
    "spo2,expected_points",
    [(91, 3), (93, 2), (95, 1), (96, 0)],
)
def test_news2_spo2_boundaries(spo2, expected_points):
    score = RiskScorer.news2(VitalSigns(spo2=spo2))
    assert score.explanation["spo2"] == expected_points


def test_news2_spo2_zero_scores_maximum_not_skipped():
    score = RiskScorer.news2(VitalSigns(spo2=0))
    assert score.explanation["spo2"] == 3.0


@pytest.mark.parametrize(
    "sbp,expected_points",
    [(90, 3), (100, 2), (110, 1), (111, 0), (219, 0), (220, 3)],
)
def test_news2_systolic_bp_boundaries(sbp, expected_points):
    score = RiskScorer.news2(VitalSigns(systolic_bp=sbp))
    assert score.explanation["systolic_bp"] == expected_points


@pytest.mark.parametrize(
    "hr,expected_points",
    [(40, 3), (41, 2), (50, 2), (51, 0), (90, 0), (91, 1), (110, 1), (111, 2), (130, 2), (131, 3)],
)
def test_news2_heart_rate_boundaries(hr, expected_points):
    """41-50 bpm scoring 2 (not 1) is the regression test for the real
    defect described in this module's docstring."""
    score = RiskScorer.news2(VitalSigns(heart_rate=hr))
    assert score.explanation["heart_rate"] == expected_points


def test_news2_heart_rate_zero_scores_maximum_not_skipped():
    # Asystole (HR=0) is the most dangerous possible reading.
    score = RiskScorer.news2(VitalSigns(heart_rate=0))
    assert score.explanation["heart_rate"] == 3.0


@pytest.mark.parametrize(
    "temp,expected_points",
    [(35.0, 3), (36.0, 1), (38.0, 0), (39.0, 1), (39.1, 2)],
)
def test_news2_temperature_boundaries(temp, expected_points):
    score = RiskScorer.news2(VitalSigns(temperature=temp))
    assert score.explanation["temperature"] == expected_points


def test_news2_gcs_below_15_adds_three_points():
    score = RiskScorer.news2(VitalSigns(gcs=14))
    assert score.explanation["consciousness"] == 3.0


def test_news2_gcs_15_adds_nothing():
    score = RiskScorer.news2(VitalSigns(gcs=15))
    assert "consciousness" not in score.explanation


def test_news2_score_of_7_is_critical():
    # respiratory_rate=25 (3) + spo2=90 (3) + hr=131 (3) alone already hits 7
    score = RiskScorer.news2(VitalSigns(respiratory_rate=25, spo2=90, heart_rate=131))
    assert score.score_value >= 7
    assert score.risk_level == RiskLevel.CRITICAL


def test_news2_score_of_exactly_6_is_high_not_critical():
    score = RiskScorer.news2(VitalSigns(systolic_bp=100, heart_rate=41, respiratory_rate=21))
    assert score.score_value == 6
    assert score.risk_level == RiskLevel.HIGH


def test_news2_partial_vitals_only_scores_whats_present():
    score = RiskScorer.news2(VitalSigns(heart_rate=75))
    assert score.score_value == 0
    assert set(score.explanation) == {"heart_rate"}


# ---------------------------------------------------------------------------
# AKI KDIGO
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ratio_creatinine,baseline,expected_stage",
    [
        (1.49, 1.0, 0),
        (1.5, 1.0, 1),
        (1.99, 1.0, 1),
        (2.0, 1.0, 2),
        (2.99, 1.0, 2),
        (3.0, 1.0, 3),
    ],
)
def test_aki_creatinine_ratio_boundaries(ratio_creatinine, baseline, expected_stage):
    score = RiskScorer.aki_kdigo(ratio_creatinine, baseline, None)
    assert score.score_value == expected_stage


def test_aki_absolute_creatinine_stage_3_without_any_baseline():
    """Regression test: a prior version of this function only checked the
    absolute >=4.0 mg/dL criterion when a baseline was also available, so a
    patient presenting with e.g. Cr 4.5 mg/dL and no known baseline (common
    at initial presentation) was scored stage 0 -- missing severe AKI
    entirely."""
    score = RiskScorer.aki_kdigo(4.5, None, None)
    assert score.score_value == 3
    assert score.risk_level == RiskLevel.CRITICAL


def test_aki_absolute_creatinine_just_under_4_without_baseline_scores_zero():
    score = RiskScorer.aki_kdigo(3.9, None, None)
    assert score.score_value == 0


def test_aki_ratio_and_absolute_combine_via_max_not_override():
    # ratio alone would say stage 1 (1.6x), but absolute value says stage 3;
    # the higher stage must win, not whichever check ran last.
    score = RiskScorer.aki_kdigo(4.8, 3.0, None)
    assert score.score_value == 3


@pytest.mark.parametrize(
    "urine_output,expected_min_stage",
    [(0.51, 0), (0.5, 0), (0.49, 1), (0.31, 1), (0.3, 1), (0.29, 3)],
)
def test_aki_urine_output_boundaries(urine_output, expected_min_stage):
    score = RiskScorer.aki_kdigo(1.0, None, urine_output)
    assert score.score_value == expected_min_stage


def test_aki_no_data_at_all_scores_zero():
    score = RiskScorer.aki_kdigo(1.0, None, None)
    assert score.score_value == 0
    assert score.risk_level == RiskLevel.LOW


def test_aki_zero_baseline_does_not_divide_by_zero():
    # baseline_creatinine=0 is a data-entry error, not a valid value; must
    # not raise ZeroDivisionError.
    score = RiskScorer.aki_kdigo(2.0, 0, None)
    assert score.score_value == 0


# ---------------------------------------------------------------------------
# CHA2DS2-VASc
# ---------------------------------------------------------------------------


def test_cha2ds2_vasc_no_risk_factors_scores_zero():
    score = RiskScorer.cha2ds2_vasc(age=40, sex="M")
    assert score.score_value == 0


@pytest.mark.parametrize("age,expected_points", [(64, 0), (65, 1), (74, 1), (75, 2)])
def test_cha2ds2_vasc_age_boundaries(age, expected_points):
    score = RiskScorer.cha2ds2_vasc(age=age, sex="M")
    assert score.score_value == expected_points


def test_cha2ds2_vasc_sex_is_case_insensitive():
    lower = RiskScorer.cha2ds2_vasc(age=40, sex="f")
    upper = RiskScorer.cha2ds2_vasc(age=40, sex="F")
    assert lower.score_value == upper.score_value == 1


def test_cha2ds2_vasc_maximum_score_is_nine():
    score = RiskScorer.cha2ds2_vasc(
        age=80,
        sex="F",
        has_chf=True,
        has_hypertension=True,
        has_diabetes=True,
        has_stroke_tia=True,
        has_vascular_disease=True,
    )
    assert score.score_value == 9
    assert score.explanation["estimated_annual_stroke_risk_pct"] == 15.2


def test_cha2ds2_vasc_published_stroke_risk_for_zero_score():
    # Cross-checked against Lip et al. Chest. 2010;137(2):263-272, Table 4.
    score = RiskScorer.cha2ds2_vasc(age=40, sex="M")
    assert score.explanation["estimated_annual_stroke_risk_pct"] == 0.0


def test_cha2ds2_vasc_male_high_risk_at_score_2():
    score = RiskScorer.cha2ds2_vasc(age=65, sex="M", has_hypertension=True)
    assert score.score_value == 2
    assert score.risk_level == RiskLevel.HIGH


def test_cha2ds2_vasc_female_needs_score_3_for_high_risk():
    # Female sex itself contributes 1 point; per the code's own risk-level
    # rule a female needs score>=3 (not just >=2) to be flagged HIGH,
    # reflecting that 1 of those points is sex alone.
    score_2 = RiskScorer.cha2ds2_vasc(age=65, sex="F")  # age 65-74 (1) + female (1) = 2
    score_3 = RiskScorer.cha2ds2_vasc(age=65, sex="F", has_hypertension=True)  # = 3
    assert score_2.risk_level == RiskLevel.LOW
    assert score_3.risk_level == RiskLevel.HIGH
