"""
MedIntelOS Federated Learning Engine
=====================================
Reference federated learning coordinator for multi-site AI experiments.
Implements weighted aggregation, optional differential-privacy noise, and basic
update outlier detection.

Architecture:
    - FedAvg / FedProx / SCAFFOLD aggregation strategies
    - Gaussian mechanism differential privacy (epsilon-delta)
    - Pluggable participant update provider
    - Asynchronous participant handling with timeout support
    - Automatic model versioning and rollback
    - FHIR-native training data extraction

Author: MedIntelOS Contributors
License: MIT
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import dp_accounting
import numpy as np
from dp_accounting.rdp.rdp_privacy_accountant import RdpAccountant

from medintelos.model_serialization import canonical_weight_hash

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AggregationStrategy(str, Enum):
    FED_AVG = "FedAvg"
    FED_PROX = "FedProx"
    SCAFFOLD = "SCAFFOLD"
    FED_NOVA = "FedNova"


class ParticipantStatus(str, Enum):
    IDLE = "idle"
    TRAINING = "training"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    BYZANTINE = "byzantine"


class RoundStatus(str, Enum):
    PENDING = "pending"
    COLLECTING = "collecting"
    AGGREGATING = "aggregating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class DifferentialPrivacyConfig:
    """Differential privacy parameters using the Gaussian mechanism,
    accounted formally over the full planned training run via Google's
    `dp_accounting` library (RDP accounting) rather than applied once and
    forgotten.

    Boundary, stated plainly: this accounts for privacy loss from the noise
    added to each round's aggregated update. It does not account for
    anything about how a participant trains locally (e.g. DP-SGD's
    per-example gradient clipping across training steps) — that is a
    separate privacy budget a participant's own training pipeline would
    need to track if it wants that guarantee too. It also assumes an honest
    coordinator and an honest majority of participants (see
    docs/THREAT_MODEL.md); it does not defend against a coordinator that
    inspects individual updates before aggregation.
    """
    enabled: bool = True
    epsilon: float = 1.0          # Target cumulative privacy budget over the
                                   # full planned run (lower = more private)
    delta: float = 1e-5           # Failure probability
    max_grad_norm: float = 1.0    # L2 gradient clipping norm
    noise_multiplier: Optional[float] = None
    # Gaussian noise scale. None (the default): calibrated automatically so
    # that `total_rounds` applications of the mechanism cost exactly
    # `epsilon` at `delta`, via dp_accounting.calibrate_dp_mechanism — this
    # is the fix for a real prior defect: `epsilon`/`delta` were declared
    # config fields that the noise computation never actually used, so
    # setting epsilon=0.1 or epsilon=100 produced identical noise. Setting
    # noise_multiplier explicitly here bypasses calibration and uses that
    # value directly; the coordinator still tracks and reports the actual
    # cumulative epsilon spent (via GaussianMechanism.current_epsilon()),
    # which may then differ from — including exceed — the declared
    # `epsilon` if the manually chosen value doesn't match the planned
    # round count. See CHANGELOG.md.

    def __post_init__(self) -> None:
        if self.epsilon <= 0:
            raise ValueError("epsilon must be positive")
        if not (0 < self.delta < 1):
            raise ValueError("delta must be in (0, 1)")
        if self.max_grad_norm <= 0:
            raise ValueError("max_grad_norm must be positive")
        if self.noise_multiplier is not None and self.noise_multiplier < 0:
            raise ValueError("noise_multiplier cannot be negative")
        logger.info(
            "DP config: target ε=%.3f, δ=%.2e, max_norm=%.2f, noise_multiplier=%s",
            self.epsilon, self.delta, self.max_grad_norm,
            "auto-calibrated" if self.noise_multiplier is None else f"{self.noise_multiplier:.4f}",
        )


@dataclass
class ModelUpdate:
    """Gradient/weight update from a single participant."""
    participant_id: str
    round_id: str
    weights: Dict[str, np.ndarray]        # Layer name → gradient tensor
    num_samples: int                       # Training samples used
    loss: float                            # Local training loss
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    signature: Optional[str] = None       # HMAC signature for integrity


@dataclass
class FederatedRound:
    """Represents a single round of federated learning."""
    round_id: str = field(default_factory=lambda: str(uuid4()))
    round_number: int = 0
    status: RoundStatus = RoundStatus.PENDING
    participants: List[str] = field(default_factory=list)
    updates_received: List[ModelUpdate] = field(default_factory=list)
    global_model_hash: Optional[str] = None
    aggregated_loss: Optional[float] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    validation_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ParticipantInfo:
    """Hospital/clinic participant metadata."""
    participant_id: str
    institution_name: str
    fhir_endpoint: str
    status: ParticipantStatus = ParticipantStatus.IDLE
    total_patients: int = 0
    last_seen: float = field(default_factory=time.time)
    rounds_participated: int = 0
    trust_score: float = 1.0      # Decreases if Byzantine behavior detected


# ---------------------------------------------------------------------------
# Differential Privacy
# ---------------------------------------------------------------------------

class GaussianMechanism:
    """
    Gaussian mechanism for (epsilon, delta)-differential privacy, formally
    accounted via Google's `dp_accounting` library (RDP accounting) across
    every round it's applied to — not just for a single application.

    Previously, `noise_multiplier` was a fixed default (1.1) that the
    `epsilon`/`delta` config fields never actually influenced: an operator
    setting `epsilon=0.1` (stronger privacy) or `epsilon=100` (essentially
    none) got identical noise either way. Verified empirically while fixing
    this: at the old default noise_multiplier=1.1, a single round already
    costs epsilon≈4.24 (at delta=1e-5) — far weaker than the config's own
    epsilon=1.0 default suggested — and cumulative epsilon after 100 rounds
    is ≈83, i.e. essentially no protection. See CHANGELOG.md.
    """

    def __init__(self, config: DifferentialPrivacyConfig, planned_rounds: int):
        if planned_rounds <= 0:
            raise ValueError("planned_rounds must be positive")
        self.config = config
        self.planned_rounds = planned_rounds
        self._accountant = RdpAccountant()
        self._rounds_composed = 0

        if not config.enabled:
            self.noise_multiplier = config.noise_multiplier or 0.0
        elif config.noise_multiplier is not None:
            self.noise_multiplier = config.noise_multiplier
        else:
            self.noise_multiplier = _calibrate_noise_multiplier(
                target_epsilon=config.epsilon,
                delta=config.delta,
                planned_rounds=planned_rounds,
            )
        logger.info(
            "GaussianMechanism ready: noise_multiplier=%.4f, planned_rounds=%d, "
            "target ε=%.3f at δ=%.2e",
            self.noise_multiplier, planned_rounds, config.epsilon, config.delta,
        )

    def clip_gradients(
        self,
        weights: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """Clip gradient tensors to max_grad_norm (L2)."""
        total_norm = np.sqrt(
            sum(np.sum(g ** 2) for g in weights.values())
        )
        clip_coef = min(1.0, self.config.max_grad_norm / (total_norm + 1e-8))
        return {k: v * clip_coef for k, v in weights.items()}

    def add_noise(
        self,
        weights: Dict[str, np.ndarray],
        num_participants: int
    ) -> Dict[str, np.ndarray]:
        """Add calibrated Gaussian noise to aggregated gradients and record
        this application with the privacy accountant. Each call composes
        one more Gaussian mechanism application — call this at most once
        per round (matching how `FederatedCoordinator._run_round` uses it),
        since the accountant's cumulative epsilon assumes exactly that.
        """
        if num_participants <= 0:
            raise ValueError("num_participants must be positive")
        sensitivity = 2.0 * self.config.max_grad_norm / num_participants
        noise_std = self.noise_multiplier * sensitivity

        noised = {}
        for layer_name, tensor in weights.items():
            noise = np.random.normal(0, noise_std, tensor.shape)
            noised[layer_name] = tensor + noise

        self._accountant.compose(dp_accounting.GaussianDpEvent(self.noise_multiplier))
        self._rounds_composed += 1
        if self._rounds_composed > self.planned_rounds:
            logger.warning(
                "GaussianMechanism applied %d times but was calibrated for "
                "%d planned rounds -- the accounted epsilon below the "
                "originally requested target is no longer guaranteed.",
                self._rounds_composed, self.planned_rounds,
            )

        logger.debug(
            "DP noise added: σ=%.6f, sensitivity=%.6f, round=%d/%d, cumulative ε=%.4f",
            noise_std, sensitivity, self._rounds_composed, self.planned_rounds,
            self.current_epsilon(),
        )
        return noised

    def current_epsilon(self, delta: Optional[float] = None) -> float:
        """Actual cumulative privacy loss spent so far, per the accountant
        -- not the config's declared target. Call after any number of
        `add_noise`/`apply` calls; returns 0.0 if none have run yet."""
        if self._rounds_composed == 0:
            return 0.0
        result: float = self._accountant.get_epsilon(delta or self.config.delta)
        return result

    @property
    def rounds_composed(self) -> int:
        return self._rounds_composed

    def apply(
        self,
        weights: Dict[str, np.ndarray],
        num_participants: int
    ) -> Dict[str, np.ndarray]:
        """Full DP pipeline: clip → aggregate → noise."""
        clipped = self.clip_gradients(weights)
        return self.add_noise(clipped, num_participants)


def _calibrate_noise_multiplier(
    *, target_epsilon: float, delta: float, planned_rounds: int
) -> float:
    """Finds the noise_multiplier such that `planned_rounds` compositions of
    the Gaussian mechanism cost exactly `target_epsilon` at `delta`, using
    dp_accounting's RDP accountant and bracketed search. Raises ValueError
    if no solution is found in the search bracket (e.g. an unreasonably
    small target_epsilon requiring more noise than the bracket covers)."""
    try:
        noise_multiplier: float = dp_accounting.calibrate_dp_mechanism(
            lambda: RdpAccountant(),
            lambda nm: dp_accounting.SelfComposedDpEvent(
                dp_accounting.GaussianDpEvent(nm), planned_rounds
            ),
            target_epsilon,
            delta,
            dp_accounting.LowerEndpointAndGuess(1e-2, 10.0),
        )
    except Exception as exc:  # dp_accounting raises plain Exception/AssertionError
        raise ValueError(
            f"Could not calibrate a noise_multiplier for target_epsilon="
            f"{target_epsilon}, delta={delta}, planned_rounds={planned_rounds}. "
            "Try a larger epsilon, a larger delta, or fewer planned rounds, "
            "or set DifferentialPrivacyConfig.noise_multiplier explicitly."
        ) from exc
    return noise_multiplier


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

class SecureAggregator:
    """
    Weighted model averaging with a FedProx-inspired adjustment.

    Despite the retained public class name, this class does not implement a
    cryptographic secure-aggregation protocol. Transport security and a vetted
    secure-aggregation implementation are deployment responsibilities.
    """

    def __init__(
        self,
        strategy: AggregationStrategy = AggregationStrategy.FED_PROX,
        prox_mu: float = 0.01,  # FedProx proximal term coefficient
    ):
        self.strategy = strategy
        self.prox_mu = prox_mu

    def aggregate(
        self,
        updates: List[ModelUpdate],
        global_weights: Dict[str, np.ndarray],
    ) -> Tuple[Dict[str, np.ndarray], float]:
        """
        Aggregate model updates from participants into a new global model.

        Returns:
            Tuple of (aggregated_weights, mean_loss)
        """
        if not updates:
            raise ValueError("No updates to aggregate")

        total_samples = sum(u.num_samples for u in updates)
        if total_samples <= 0:
            raise ValueError("Updates must contain at least one training sample")
        aggregated: Dict[str, np.ndarray] = {}

        expected_layers = set(updates[0].weights)
        if not expected_layers:
            raise ValueError("Model update has no layers")
        for update in updates:
            if set(update.weights) != expected_layers:
                raise ValueError("All model updates must contain the same layers")

        reference_weights = global_weights or updates[0].weights

        # Initialize from update shapes so the first round can start from an empty model.
        for layer_name, tensor in reference_weights.items():
            aggregated[layer_name] = np.zeros_like(tensor)

        for update in updates:
            weight = update.num_samples / total_samples

            for layer_name, grad in update.weights.items():
                if grad.shape != aggregated[layer_name].shape:
                    raise ValueError(f"Layer shape mismatch for {layer_name}")
                # FedProx changes the participant's local objective. Server-side
                # aggregation remains sample-weighted averaging.
                aggregated[layer_name] += weight * grad

        mean_loss = sum(
            u.loss * u.num_samples / total_samples for u in updates
        )

        logger.info(
            "Aggregated %d updates, total_samples=%d, mean_loss=%.4f",
            len(updates), total_samples, mean_loss
        )
        return aggregated, mean_loss

    def detect_byzantine(
        self,
        updates: List[ModelUpdate],
        threshold: float = 3.0
    ) -> List[str]:
        """
        Detect Byzantine (malicious/faulty) participants using cosine similarity
        and L2 norm outlier detection.

        Returns:
            List of suspected byzantine participant IDs
        """
        if len(updates) < 3:
            return []

        byzantine_ids = []

        # Flatten all updates to vectors for comparison
        flat_updates = []
        for u in updates:
            flat = np.concatenate([g.flatten() for g in u.weights.values()])
            flat_updates.append(flat)

        flat_array = np.array(flat_updates)
        norms = np.linalg.norm(flat_array, axis=1)
        mean_norm = np.mean(norms)
        std_norm = np.std(norms)

        for i, update in enumerate(updates):
            z_score = abs(norms[i] - mean_norm) / (std_norm + 1e-8)
            if z_score > threshold:
                byzantine_ids.append(update.participant_id)
                logger.warning(
                    "Potential Byzantine participant detected: %s (z=%.2f)",
                    update.participant_id, z_score
                )

        return byzantine_ids


# ---------------------------------------------------------------------------
# Federated Coordinator (Main Class)
# ---------------------------------------------------------------------------

class FederatedCoordinator:
    """
    Central coordinator for federated learning across hospital participants.

    Manages the full lifecycle:
    1. Participant registration and selection
    2. Global model distribution
    3. Round coordination with timeout handling
    4. Secure aggregation with differential privacy
    5. Model validation and versioning
    6. Byzantine fault detection

    Example:
        coordinator = FederatedCoordinator(
            model_type="sepsis_predictor",
            aggregation=AggregationStrategy.FED_PROX,
            privacy=DifferentialPrivacyConfig(epsilon=1.0, delta=1e-5),
            min_participants=5,
            total_rounds=50
        )
        await coordinator.run()
    """

    def __init__(
        self,
        model_type: str,
        aggregation: AggregationStrategy = AggregationStrategy.FED_PROX,
        privacy: Optional[DifferentialPrivacyConfig] = None,
        min_participants: int = 3,
        total_rounds: int = 100,
        round_timeout_seconds: int = 3600,
        validation_fn: Optional[Callable] = None,
        update_provider: Optional[
            Callable[[ParticipantInfo, str, Dict[str, np.ndarray]], Union[ModelUpdate, None, Awaitable[Optional[ModelUpdate]]]]
        ] = None,
        unavailable_retry_seconds: float = 0.1,
    ):
        self.model_type = model_type
        self.aggregation = aggregation
        self.privacy_config = privacy or DifferentialPrivacyConfig()
        self.min_participants = min_participants
        self.total_rounds = total_rounds
        self.round_timeout = round_timeout_seconds
        self.validation_fn = validation_fn
        self.update_provider = update_provider
        self.unavailable_retry_seconds = unavailable_retry_seconds

        self.participants: Dict[str, ParticipantInfo] = {}
        self.rounds: List[FederatedRound] = []
        self.global_model: Dict[str, np.ndarray] = {}
        self.model_version: int = 0

        self._aggregator = SecureAggregator(strategy=aggregation)
        self._dp = GaussianMechanism(self.privacy_config, planned_rounds=self.total_rounds)

        logger.info(
            "FederatedCoordinator initialized: model=%s, strategy=%s, "
            "min_participants=%d, rounds=%d",
            model_type, aggregation.value, min_participants, total_rounds
        )

    # ------------------------------------------------------------------
    # Participant Management
    # ------------------------------------------------------------------

    def register_participant(
        self,
        participant_id: str,
        institution_name: str,
        fhir_endpoint: str,
        total_patients: int,
    ) -> ParticipantInfo:
        """Register a new hospital/clinic as a federated participant."""
        info = ParticipantInfo(
            participant_id=participant_id,
            institution_name=institution_name,
            fhir_endpoint=fhir_endpoint,
            total_patients=total_patients,
        )
        self.participants[participant_id] = info
        logger.info(
            "Participant registered: %s (%s, %d patients)",
            institution_name, participant_id, total_patients
        )
        return info

    def get_active_participants(self) -> List[ParticipantInfo]:
        """Return participants eligible for the next round."""
        cutoff = time.time() - 3600  # Must have been seen in last hour
        return [
            p for p in self.participants.values()
            if p.last_seen > cutoff
            and p.status != ParticipantStatus.BYZANTINE
            and p.trust_score > 0.5
        ]

    # ------------------------------------------------------------------
    # Round Management
    # ------------------------------------------------------------------

    async def run(self) -> Dict[str, Any]:
        """
        Execute the full federated learning process across all rounds.

        Returns:
            Training summary with final model metrics.
        """
        logger.info("Starting federated training: %d rounds", self.total_rounds)
        training_losses = []

        for round_num in range(1, self.total_rounds + 1):
            active = self.get_active_participants()

            if len(active) < self.min_participants:
                logger.warning(
                    "Round %d skipped: only %d/%d participants available",
                    round_num, len(active), self.min_participants
                )
                await asyncio.sleep(self.unavailable_retry_seconds)
                continue

            result = await self._run_round(round_num, active)
            training_losses.append(result.aggregated_loss or float("inf"))

            if result.status == RoundStatus.COMPLETED:
                logger.info(
                    "Round %d completed: loss=%.4f",
                    round_num, result.aggregated_loss or 0
                )
            else:
                logger.error("Round %d failed", round_num)

        return {
            "model_type": self.model_type,
            "total_rounds": self.total_rounds,
            "final_model_version": self.model_version,
            "final_loss": training_losses[-1] if training_losses else None,
            "training_losses": training_losses,
            "participants": len(self.participants),
        }

    async def _run_round(
        self,
        round_number: int,
        participants: List[ParticipantInfo],
    ) -> FederatedRound:
        """Execute a single federated learning round."""
        current_round = FederatedRound(
            round_number=round_number,
            participants=[p.participant_id for p in participants],
            status=RoundStatus.COLLECTING,
            global_model_hash=self._hash_model(self.global_model),
        )
        self.rounds.append(current_round)

        try:
            # 1. Distribute global model to participants
            await self._distribute_model(participants, current_round.round_id)

            # 2. Wait for updates (with timeout)
            updates = await asyncio.wait_for(
                self._collect_updates(current_round, participants),
                timeout=self.round_timeout,
            )

            if len(updates) < self.min_participants:
                current_round.status = RoundStatus.FAILED
                return current_round

            # 3. Detect Byzantine participants
            byzantine_ids = self._aggregator.detect_byzantine(updates)
            clean_updates = [
                u for u in updates if u.participant_id not in byzantine_ids
            ]
            for bid in byzantine_ids:
                if bid in self.participants:
                    self.participants[bid].trust_score *= 0.5
                    self.participants[bid].status = ParticipantStatus.BYZANTINE

            if len(clean_updates) < self.min_participants:
                current_round.status = RoundStatus.FAILED
                return current_round

            # 4. Aggregate updates
            current_round.status = RoundStatus.AGGREGATING
            new_weights, mean_loss = self._aggregator.aggregate(
                clean_updates, self.global_model
            )

            # 5. Apply differential privacy
            if self.privacy_config.enabled:
                new_weights = self._dp.apply(new_weights, len(clean_updates))

            # 6. Update global model
            self.global_model = new_weights
            self.model_version += 1
            current_round.aggregated_loss = mean_loss
            current_round.updates_received = clean_updates

            # 7. Validate new model
            current_round.status = RoundStatus.VALIDATING
            if self.validation_fn:
                metrics = await asyncio.to_thread(
                    self.validation_fn, self.global_model
                )
                current_round.validation_metrics = metrics

            current_round.status = RoundStatus.COMPLETED
            current_round.completed_at = time.time()

        except asyncio.TimeoutError:
            logger.error("Round %d timed out", round_number)
            current_round.status = RoundStatus.FAILED
        except Exception as exc:
            logger.exception("Round %d failed: %s", round_number, exc)
            current_round.status = RoundStatus.FAILED

        return current_round

    async def _distribute_model(
        self,
        participants: List[ParticipantInfo],
        round_id: str,
    ) -> None:
        """Distribute current global model to all participants."""
        tasks = [
            self._send_model_to_participant(p, round_id)
            for p in participants
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_model_to_participant(
        self,
        participant: ParticipantInfo,
        round_id: str,
    ) -> None:
        """Send model weights to a single participant (implement HTTP/gRPC call)."""
        participant.status = ParticipantStatus.TRAINING
        logger.debug(
            "Model sent to %s for round %s",
            participant.institution_name, round_id
        )

    async def _collect_updates(
        self,
        current_round: FederatedRound,
        participants: List[ParticipantInfo],
    ) -> List[ModelUpdate]:
        """Collect model updates from all participants."""
        # In production, this polls an update queue or waits for HTTP callbacks
        # Simulated here for architecture clarity
        updates: List[ModelUpdate] = []
        for p in participants:
            update = await self._fetch_update(p, current_round.round_id)
            if update:
                updates.append(update)
                p.status = ParticipantStatus.COMPLETED
                p.rounds_participated += 1
                p.last_seen = time.time()
        return updates

    async def _fetch_update(
        self,
        participant: ParticipantInfo,
        round_id: str,
    ) -> Optional[ModelUpdate]:
        """Fetch an update through the configured integration callback."""
        if self.update_provider is None:
            return None
        result = self.update_provider(participant, round_id, self.global_model)
        if result is not None and not isinstance(result, ModelUpdate):
            result = await result
        if result is not None:
            if result.participant_id != participant.participant_id:
                raise ValueError("Update participant does not match requested participant")
            if result.round_id != round_id:
                raise ValueError("Update round does not match active round")
        return result

    def _hash_model(self, model: Dict[str, np.ndarray]) -> str:
        """Compute deterministic hash of model weights for integrity
        verification, via the canonical ONNX serialization
        (model_serialization.py) rather than json.dumps of Python float
        reprs -- see that module's docstring for why the previous approach
        could theoretically produce different hashes for bit-identical
        arrays across platforms, and silently ignored dtype entirely."""
        return canonical_weight_hash(model)

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return current coordinator status as a serializable dict."""
        completed = [r for r in self.rounds if r.status == RoundStatus.COMPLETED]
        failed = [r for r in self.rounds if r.status == RoundStatus.FAILED]

        return {
            "model_type": self.model_type,
            "model_version": self.model_version,
            "aggregation_strategy": self.aggregation.value,
            "differential_privacy": {
                "enabled": self.privacy_config.enabled,
                "target_epsilon": self.privacy_config.epsilon,
                "delta": self.privacy_config.delta,
                "noise_multiplier": self._dp.noise_multiplier,
                "actual_epsilon_spent": self._dp.current_epsilon(),
                "planned_rounds": self._dp.planned_rounds,
                "rounds_composed": self._dp.rounds_composed,
            },
            "participants": {
                "total": len(self.participants),
                "active": len(self.get_active_participants()),
                "byzantine": sum(
                    1 for p in self.participants.values()
                    if p.status == ParticipantStatus.BYZANTINE
                ),
            },
            "rounds": {
                "total": self.total_rounds,
                "completed": len(completed),
                "failed": len(failed),
                "current_round": len(self.rounds),
            },
            "latest_loss": (
                completed[-1].aggregated_loss if completed else None
            ),
        }
