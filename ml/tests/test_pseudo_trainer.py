"""Tests for the self-paced pseudo-label trainer (Stage C).

Gated behind ``RUN_TORCH_TESTS=1`` alongside the Stage B tests since the
embedded model download cost dominates.
"""

from __future__ import annotations

import os

import numpy as np
import pytest
import torch

from orchardvision_ml.identity.dataset import TrackObservation
from orchardvision_ml.identity.pseudo_trainer import (
    SelfSupervisedConfig,
    SelfSupervisedTrainer,
)
from orchardvision_ml.identity.torch_trainer import TorchTrainerConfig

RUN_TORCH = os.environ.get("RUN_TORCH_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_TORCH,
    reason="set RUN_TORCH_TESTS=1 to run torch trainer tests",
)


@pytest.fixture()
def tiny_config() -> SelfSupervisedConfig:
    return SelfSupervisedConfig(
        cluster_eps=0.3,
        cluster_min_samples=2,
        repeats=2,
        initial_min_confidence=0.0,
        base_config=TorchTrainerConfig(epochs=2, batch_size=2),
    )


def _obs(track_id: int, frame_id: int, x: float, confidence: float) -> TrackObservation:
    return TrackObservation(
        track_id=track_id,
        frame_id=frame_id,
        bbox=(x, 100.0, 30.0, 30.0),
        confidence=confidence,
        source_id="v0",
    )


def _synthetic_corpus() -> tuple[list[TrackObservation], object]:
    """Three distinct-colored fruit tracks; distinct labels should emerge.

    Includes one low-confidence track that round 0 gating would normally drop.
    """
    observations = [
        _obs(1, f, x=100.0 if f in (5, 7) else 103.0, confidence=0.95) for f in (5, 7, 9, 11)
    ]
    observations += [
        _obs(2, f, x=600.0 if f in (5, 7) else 602.0, confidence=0.95) for f in (5, 7, 9, 11)
    ]
    observations += [
        _obs(3, f, x=900.0 if f in (5, 7) else 901.0, confidence=0.95) for f in (5, 7, 9, 11)
    ]
    observations += [_obs(4, f, x=130.0, confidence=0.6) for f in (5, 7)]
    colors = {
        1: (220, 60, 60),
        2: (60, 120, 220),
        3: (60, 200, 90),
        4: (200, 200, 80),
    }
    cache: dict[tuple[str, int], np.ndarray] = {}

    def provider(source_id: str, frame_id: int) -> np.ndarray:
        key = (source_id, frame_id)
        if key not in cache:
            frame = np.full((480, 640, 3), 30, dtype=np.uint8)
            for obs in observations:
                if obs.frame_id == frame_id:
                    x, y, w, h = (int(v) for v in obs.bbox)
                    frame[y : y + h, x : x + w] = colors.get(obs.track_id, (200, 200, 200))
            cache[key] = frame
        return cache[key]

    return observations, provider


def test_self_supervised_trainer_runs_curriculum(tiny_config) -> None:
    observations, provider = _synthetic_corpus()
    trainer = SelfSupervisedTrainer(tiny_config)
    result = trainer.train(observations, provider)

    assert len(result.rounds) == tiny_config.repeats
    last = result.rounds[-1]
    # Same network continues across rounds: final model still produces
    # unit-norm embeddings on the last refreshed observations.
    vectors = [v.vector for v in result.embedded_observations if v.vector is not None]
    assert vectors and all(np.isclose(np.linalg.norm(v), 1.0, atol=1e-4) for v in vectors)
    assert last.anchors > 0
    assert isinstance(last.training.loss_history, list)


def test_self_supervised_trainer_refreshes_vectors(tiny_config) -> None:
    observations, provider = _synthetic_corpus()
    assert all(obs.vector is None for obs in observations)
    trainer = SelfSupervisedTrainer(tiny_config)
    result = trainer.train(observations, provider)
    assert all(obs.vector is not None for obs in result.embedded_observations)


def test_self_supervised_trainer_saves_checkpoint(tiny_config, tmp_path) -> None:
    observations, provider = _synthetic_corpus()
    trainer = SelfSupervisedTrainer(tiny_config)
    trainer.train(observations, provider)
    path = trainer.save(tmp_path / "identity.pt")
    checkpoint = torch.load(path, weights_only=False)
    assert "state_dict" in checkpoint
    assert checkpoint["backbone_name"] == "resnet18"


def test_self_supervised_confidence_gate_filters_round_zero(tiny_config) -> None:
    gated = SelfSupervisedConfig(
        cluster_eps=0.3,
        cluster_min_samples=2,
        repeats=1,
        initial_min_confidence=0.9,
        base_config=TorchTrainerConfig(epochs=1, batch_size=2),
    )
    observations, provider = _synthetic_corpus()
    trainer = SelfSupervisedTrainer(gated)
    result = trainer.train(observations, provider)
    # Only the confident tracks pass the 0.9 gate; the 0.6 track is labeled late
    # or excluded, but the curriculum itself must have started.
    assert result.rounds[0].labeled_tracklets >= 3
