import numpy as np
import pytest

from medintelos.federated import (
    AggregationStrategy,
    DifferentialPrivacyConfig,
    FederatedCoordinator,
    ModelUpdate,
    RoundStatus,
    SecureAggregator,
)


def test_first_round_aggregation_initializes_layers() -> None:
    updates = [
        ModelUpdate("a", "r1", {"weight": np.array([1.0, 3.0])}, 10, 0.4),
        ModelUpdate("b", "r1", {"weight": np.array([3.0, 5.0])}, 30, 0.2),
    ]

    weights, loss = SecureAggregator(AggregationStrategy.FED_AVG).aggregate(updates, {})

    np.testing.assert_allclose(weights["weight"], np.array([2.5, 4.5]))
    assert loss == pytest.approx(0.25)


@pytest.mark.asyncio
async def test_coordinator_runs_with_injected_update_provider() -> None:
    def provider(participant, round_id, _global_model):
        value = 1.0 if participant.participant_id == "a" else 3.0
        return ModelUpdate(
            participant_id=participant.participant_id,
            round_id=round_id,
            weights={"weight": np.array([value])},
            num_samples=10,
            loss=value / 10,
        )

    coordinator = FederatedCoordinator(
        model_type="demo",
        aggregation=AggregationStrategy.FED_AVG,
        privacy=DifferentialPrivacyConfig(enabled=False),
        min_participants=2,
        total_rounds=1,
        update_provider=provider,
    )
    coordinator.register_participant("a", "Hospital A", "https://a.example/fhir", 100)
    coordinator.register_participant("b", "Hospital B", "https://b.example/fhir", 100)

    result = await coordinator.run()

    assert result["final_model_version"] == 1
    assert coordinator.rounds[0].status == RoundStatus.COMPLETED
    np.testing.assert_allclose(coordinator.global_model["weight"], np.array([2.0]))
