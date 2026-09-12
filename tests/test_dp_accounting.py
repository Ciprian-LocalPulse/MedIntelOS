"""Tests for formal differential-privacy accounting in federated.py.

Before this, `noise_multiplier` was a fixed default (1.1) that the declared
`epsilon`/`delta` never actually influenced -- these tests are, in part,
regressions proving that's fixed: the actual cumulative epsilon spent now
matches whatever target was declared, computed via Google's `dp_accounting`
library (RDP accounting), not by hand.
"""

from __future__ import annotations

import numpy as np
import pytest

from medintelos.federated import DifferentialPrivacyConfig, GaussianMechanism


def _weights() -> dict[str, np.ndarray]:
    return {"layer1": np.ones((4,)), "layer2": np.ones((2, 2))}


def test_calibrated_noise_multiplier_hits_target_epsilon_exactly():
    config = DifferentialPrivacyConfig(epsilon=1.0, delta=1e-5)
    mechanism = GaussianMechanism(config, planned_rounds=10)
    for _ in range(10):
        mechanism.add_noise(_weights(), num_participants=5)
    assert mechanism.current_epsilon() == pytest.approx(1.0, rel=1e-3)


@pytest.mark.parametrize("target_epsilon,rounds", [(0.5, 5), (1.0, 1), (3.0, 50)])
def test_calibration_hits_target_across_various_configs(target_epsilon, rounds):
    config = DifferentialPrivacyConfig(epsilon=target_epsilon, delta=1e-5)
    mechanism = GaussianMechanism(config, planned_rounds=rounds)
    for _ in range(rounds):
        mechanism.add_noise(_weights(), num_participants=3)
    assert mechanism.current_epsilon() == pytest.approx(target_epsilon, rel=1e-3)


def test_more_planned_rounds_requires_more_noise_for_the_same_epsilon():
    """Regression for the exact defect being fixed: previously noise was a
    fixed constant regardless of how many rounds were planned. Composing a
    fixed privacy budget over more rounds must now require *more* noise per
    round (each round contributes a smaller slice of the same total
    budget)."""
    few_rounds = GaussianMechanism(
        DifferentialPrivacyConfig(epsilon=1.0, delta=1e-5), planned_rounds=5
    )
    many_rounds = GaussianMechanism(
        DifferentialPrivacyConfig(epsilon=1.0, delta=1e-5), planned_rounds=50
    )
    assert many_rounds.noise_multiplier > few_rounds.noise_multiplier


def test_epsilon_is_zero_before_any_round_runs():
    config = DifferentialPrivacyConfig(epsilon=1.0, delta=1e-5)
    mechanism = GaussianMechanism(config, planned_rounds=10)
    assert mechanism.current_epsilon() == 0.0


def test_epsilon_accumulates_monotonically_across_rounds():
    config = DifferentialPrivacyConfig(epsilon=5.0, delta=1e-5)
    mechanism = GaussianMechanism(config, planned_rounds=10)
    previous = 0.0
    for _ in range(10):
        mechanism.add_noise(_weights(), num_participants=4)
        current = mechanism.current_epsilon()
        assert current > previous
        previous = current


def test_explicit_noise_multiplier_bypasses_calibration():
    config = DifferentialPrivacyConfig(epsilon=1.0, delta=1e-5, noise_multiplier=2.5)
    mechanism = GaussianMechanism(config, planned_rounds=10)
    assert mechanism.noise_multiplier == 2.5


def test_explicit_noise_multiplier_can_exceed_declared_target_honestly():
    """If an operator manually sets a noise_multiplier too low for their
    stated epsilon/round-count, the accountant must report the real
    (larger, worse) spent epsilon rather than silently keeping the
    declared target -- this is exactly the dishonesty being fixed."""
    config = DifferentialPrivacyConfig(epsilon=1.0, delta=1e-5, noise_multiplier=1.1)
    mechanism = GaussianMechanism(config, planned_rounds=1)
    mechanism.add_noise(_weights(), num_participants=5)
    # At noise_multiplier=1.1 (the old hardcoded default), one round alone
    # already costs roughly epsilon=4.24 at delta=1e-5 -- far above the
    # declared target of 1.0.
    assert mechanism.current_epsilon() > config.epsilon


def test_disabled_dp_skips_calibration_entirely():
    # Must not raise, and must not attempt calibration, when DP is off.
    config = DifferentialPrivacyConfig(enabled=False, epsilon=1.0, delta=1e-5)
    mechanism = GaussianMechanism(config, planned_rounds=10)
    assert mechanism.rounds_composed == 0


def test_planned_rounds_must_be_positive():
    config = DifferentialPrivacyConfig(epsilon=1.0, delta=1e-5)
    with pytest.raises(ValueError):
        GaussianMechanism(config, planned_rounds=0)


def test_noise_multiplier_none_is_the_default_and_triggers_calibration():
    config = DifferentialPrivacyConfig(epsilon=1.0, delta=1e-5)
    assert config.noise_multiplier is None
    mechanism = GaussianMechanism(config, planned_rounds=10)
    assert mechanism.noise_multiplier is not None
    assert mechanism.noise_multiplier > 0


def test_negative_explicit_noise_multiplier_is_rejected():
    with pytest.raises(ValueError):
        DifferentialPrivacyConfig(noise_multiplier=-1.0)


def test_rounds_composed_tracks_number_of_add_noise_calls():
    config = DifferentialPrivacyConfig(epsilon=2.0, delta=1e-5)
    mechanism = GaussianMechanism(config, planned_rounds=3)
    assert mechanism.rounds_composed == 0
    mechanism.add_noise(_weights(), num_participants=2)
    assert mechanism.rounds_composed == 1
    mechanism.add_noise(_weights(), num_participants=2)
    assert mechanism.rounds_composed == 2
