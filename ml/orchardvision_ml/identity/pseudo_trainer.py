"""Self-paced pseudo-label identity training loop.

Ties together the Stage A–C pieces into the full self-supervised procedure:

1. Embed every visible observation with the current model (``IdentityEmbeddingNet``).
2. Cluster sub-tracklet *centroids* into pseudo identities with DBSCAN.
3. Build contrastive pairs from the pseudo labels (``build_label_pairs``).
4. Train the same network further on those pairs (``TorchContrastiveTrainer``).
5. Relax the confidence gate each round so progressively noisier pseudo labels
   are admitted (self-paced curriculum, SpCL-style).

Only the "clean" (reliable, high-confidence) sub-tracklets seed clusters in the
early rounds, which limits confirmation-bias errors (PCL-style filtering).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from .cluster import assign_centroid_pseudo_labels
from .dataset import TrackletDataset, TrackletPartitioner, TrackObservation
from .torch_trainer import (
    FrameProvider,
    IdentityEmbeddingNet,
    TorchContrastiveTrainer,
    TorchTrainerConfig,
    TorchTrainingResult,
)
from .training import PairOptions

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .dataset import SubTracklet

__all__ = [
    "SelfSupervisedConfig",
    "SelfSupervisedResult",
    "SelfSupervisedTrainer",
]

_NO_TORCH = "torch is required for the self-supervised identity trainer"


@dataclass(frozen=True, slots=True)
class SelfSupervisedConfig:
    """Curriculum hyper-parameters for pseudo-label self-training.

    Attributes:
        cluster_eps: DBSCAN neighbor threshold (cosine distance) over
            sub-tracklet centroid embeddings.
        cluster_min_samples: DBSCAN minimum samples to seed a cluster.
        repeats: Number of cluster → train rounds.
        initial_min_confidence: Confidence gate for round 0 sub-tracklets.
        confidence_floor: Lowest confidence gate allowed as the curriculum
            relaxes.
        confidence_decay: Gate multiplier between rounds (``0.95`` admits
            ~``1 - 0.95^repeats`` more relative noise by the final round).
        pair_options: Temporal-window, spatial-gate and hard-mining options
            forwarded to :class:`TrackletDataset`.
        partitioner: Sub-tracklet cleaner forwarded to :class:`TrackletDataset`.
        base_config: Contrastive trainer config (backbone, heads, lr…).
    """

    cluster_eps: float = 0.3
    cluster_min_samples: int = 3
    repeats: int = 3
    initial_min_confidence: float = 0.85
    confidence_floor: float = 0.5
    confidence_decay: float = 0.95
    pair_options: PairOptions = PairOptions()
    partitioner: TrackletPartitioner = TrackletPartitioner()
    base_config: TorchTrainerConfig = TorchTrainerConfig()


@dataclass(frozen=True, slots=True)
class _RoundResult:
    threshold: float
    labeled_tracklets: int
    unlabeled_tracklets: int
    clusters: int
    anchors: int
    training: TorchTrainingResult


@dataclass(frozen=True, slots=True)
class SelfSupervisedResult:
    """Outcome of one self-training run across all rounds.

    Attributes:
        rounds: Per-round curriculum statistics and training results.
        embedded_observations: Final observations with ``vector`` refreshed by
            the last embedding pass (useful for downstream evaluation without
            recomputing embeddings).
    """

    rounds: tuple[_RoundResult, ...]
    embedded_observations: tuple[TrackObservation, ...]

    def final_separation(self) -> float:
        """Positive-minus-negative cosine gap after the last round."""
        return self.rounds[-1].training.separation() if self.rounds else 0.0


class SelfSupervisedTrainer:
    """Runs the self-paced cluster → contrastive-train curriculum in place.

    The underlying :class:`IdentityEmbeddingNet` is trained continuously across
    rounds (no reset), so round ``k + 1`` starts from the embeddings learned by
    round ``k``.

    Attributes:
        config: Curriculum and trainer configuration.
    """

    def __init__(self, config: SelfSupervisedConfig | None = None) -> None:
        try:
            import torch
        except ImportError:  # pragma: no cover - mock environments may lack torch
            # mypy infers `torch` as the Module that the import binds and
            # rejects assigning None to it. This is the standard
            # optional-dependency guard, which mypy cannot express: the name
            # genuinely is a Module or None at runtime.
            torch = None  # type: ignore[assignment]
        if torch is None:  # pragma: no cover
            raise ImportError(_NO_TORCH) from None
        self.config = config or SelfSupervisedConfig()
        self.trainer = TorchContrastiveTrainer(self.config.base_config)

    @property
    def net(self) -> IdentityEmbeddingNet:
        return self.trainer.net

    def train(
        self,
        observations: Sequence[TrackObservation],
        frames: FrameProvider,
    ) -> SelfSupervisedResult:
        """Execute the self-paced pseudo-label curriculum.

        Args:
            observations: Detection observations with ``source_id``, ``frame_id``
                and ``bbox`` set; ``vector`` may be ``None`` (it is computed
                fresh each round from the current model).
            frames: ``source_id, frame_id`` → BGR frame provider.

        Returns:
            Per-round outcomes (loss, similarities, pseudo-label statistics).
        """
        rounds: list[_RoundResult] = []
        current = list(observations)
        final_observations = tuple(current)
        threshold = self.config.initial_min_confidence
        for _ in range(self.config.repeats):
            current = self._embed_observations(current, frames)
            dataset = TrackletDataset(
                current,
                pair_options=self.config.pair_options,
                partitioner=self.config.partitioner,
            )
            labels, unlabeled, clusters = self._cluster_reliable(dataset.subtracklets, threshold)
            pairs = dataset.build_label_pairs(labels)
            result = self.trainer.train(pairs, frames)
            rounds.append(
                _RoundResult(
                    threshold=threshold,
                    labeled_tracklets=len(labels),
                    unlabeled_tracklets=len(unlabeled),
                    clusters=clusters,
                    anchors=len(pairs),
                    training=result,
                )
            )
            threshold = max(threshold * self.config.confidence_decay, self.config.confidence_floor)
            final_observations = tuple(current)
        return SelfSupervisedResult(rounds=tuple(rounds), embedded_observations=final_observations)

    def _embed_observations(
        self, observations: Sequence[TrackObservation], frames: FrameProvider
    ) -> list[TrackObservation]:
        """Refresh every observation's ``vector`` in evaluation mode."""
        if not observations:
            return list(observations)
        import torch

        net = self.net
        net.model.eval()
        embedded: list[TrackObservation] = []
        with torch.inference_mode():
            for obs in observations:
                crop = _crop(frames, obs, net.input_size)
                tensor = torch.as_tensor(crop[None, ...]).float().to(net.device)
                vector = net(tensor).squeeze(0).cpu().numpy()
                embedded.append(replace(obs, vector=vector.astype("float32")))
        net.model.train()
        return embedded

    def _cluster_reliable(
        self, subtracklets: Sequence[SubTracklet], threshold: float
    ) -> tuple[dict[int, int], list[int], int]:
        """Cluster only sub-tracklets passing the current confidence gate."""
        eligible: list[tuple[int, SubTracklet]] = []
        for index, sub in enumerate(subtracklets):
            if sub.is_confident and min(obs.confidence for obs in sub.observations) >= threshold:
                eligible.append((index, sub))
        if not eligible:
            return {}, [], 0
        indices = [index for index, _ in eligible]
        subs = [sub for _, sub in eligible]
        result = assign_centroid_pseudo_labels(
            subs, self.config.cluster_eps, self.config.cluster_min_samples
        )
        labels = {indices[source]: label for source, label in result.labels.items()}
        unlabeled = [indices[source] for source in result.unlabeled_indices]
        return labels, unlabeled, result.cluster_count

    def save(self, path: str | Path) -> str:
        return self.trainer.save(path)


def _crop(frames: FrameProvider, obs: TrackObservation, input_size: int):
    from .dataset import crop_observation

    return crop_observation(frames(obs.source_id, obs.frame_id), obs, input_size)
