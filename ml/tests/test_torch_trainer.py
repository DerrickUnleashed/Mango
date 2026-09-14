"""Tests for the PyTorch contrastive trainer (Stage B).

These tests only run when ``RUN_TORCH_TESTS=1`` is set, since the first use
downloads the ImageNet-pretrained ResNet18 weights (~45 MB literal).
"""

from __future__ import annotations

import os

import numpy as np
import pytest
import torch

from orchardvision_ml.identity.dataset import (
    TrackletDataset,
    TrackletPartitioner,
    TrackObservation,
)
from orchardvision_ml.identity.torch_trainer import (
    IdentityEmbeddingNet,
    TorchContrastiveTrainer,
    TorchTrainerConfig,
)
from orchardvision_ml.identity.training import PairOptions

RUN_TORCH = os.environ.get("RUN_TORCH_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_TORCH,
    reason="set RUN_TORCH_TESTS=1 to run torch trainer tests",
)

TRACK_COLORS = {
    3: (220, 60, 60),
    9: (60, 120, 220),
    17: (60, 200, 90),
}


def _build_synthetic_frames() -> tuple[list[TrackObservation], object]:
    """Two-frame observations per track; returns observations + frame provider."""
    observations = [
        TrackObservation(3, frame_id=5, bbox=(100.0, 100.0, 30.0, 30.0), confidence=0.9),
        TrackObservation(3, frame_id=6, bbox=(103.0, 100.0, 30.0, 30.0), confidence=0.9),
        TrackObservation(9, frame_id=5, bbox=(600.0, 100.0, 30.0, 30.0), confidence=0.9),
        TrackObservation(9, frame_id=6, bbox=(602.0, 100.0, 30.0, 30.0), confidence=0.9),
        TrackObservation(17, frame_id=5, bbox=(900.0, 100.0, 30.0, 30.0), confidence=0.9),
        TrackObservation(17, frame_id=6, bbox=(901.0, 100.0, 30.0, 30.0), confidence=0.9),
    ]
    cache: dict[tuple[str, int], np.ndarray] = {}

    def draw(frame: np.ndarray, obs: TrackObservation) -> None:
        color = TRACK_COLORS.get(obs.track_id, (200, 200, 200))
        x, y, w, h = (int(v) for v in obs.bbox)
        frame[y : y + h, x : x + w] = color

    def provider(source_id: str, frame_id: int) -> np.ndarray:
        key = (source_id, frame_id)
        if key not in cache:
            frame = np.full((480, 640, 3), 30, dtype=np.uint8)
            for obs in observations:
                if obs.frame_id == frame_id:
                    draw(frame, obs)
            cache[key] = frame
        return cache[key]

    return observations, provider


def test_identity_embedding_net_shape_and_units() -> None:
    net = IdentityEmbeddingNet(
        backbone_name="resnet18",
        embed_dim=16,
        hidden_dim=32,
        input_size=64,
        device="cpu",
    )
    batch = torch.rand(2, 3, net.input_size, net.input_size)
    embeddings = net(batch)
    assert embeddings.shape == (2, 16)
    assert torch.allclose(embeddings.norm(dim=1), torch.ones(2), atol=1e-3)


def test_contrastive_trainer_separates_positives() -> None:
    observations, provider = _build_synthetic_frames()
    dataset = TrackletDataset(
        observations,
        pair_options=PairOptions(max_frames_apart=2, min_center_distance=200.0, temperature=0.2),
        partitioner=TrackletPartitioner(min_sub_length=1),
    )
    pairs = dataset.build_pairs()
    assert all(p.positive is not None for p in pairs)
    assert all(p.negatives for p in pairs)

    trainer = TorchContrastiveTrainer(
        config=TorchTrainerConfig(
            backbone="resnet18",
            embed_dim=16,
            hidden_dim=32,
            input_size=64,
            temperature=0.2,
            learning_rate=1e-3,
            epochs=3,
            batch_size=2,
            device="cpu",
            seed=0,
        )
    )
    result = trainer.train(pairs, provider)
    assert len(result.loss_history) == 3
    assert all(loss == loss and not np.isinf(loss) for loss in result.loss_history)
    assert result.positive_similarity > result.negative_similarity
    assert result.separation() > 0.0


def test_contrastive_trainer_checkpoint_roundtrip(tmp_path) -> None:
    observations, provider = _build_synthetic_frames()
    del provider
    TrackletDataset(
        observations,
        pair_options=PairOptions(max_frames_apart=2, min_center_distance=200.0),
        partitioner=TrackletPartitioner(min_sub_length=1),
    )
    trainer = TorchContrastiveTrainer(
        config=TorchTrainerConfig(
            backbone="resnet18",
            embed_dim=16,
            hidden_dim=32,
            input_size=64,
            learning_rate=1e-4,
            epochs=1,
            batch_size=2,
            device="cpu",
            seed=0,
        )
    )
    checkpoint = trainer.save(tmp_path / "trainer.pt")
    assert os.path.isfile(checkpoint)

    reloaded = TorchContrastiveTrainer(
        config=TorchTrainerConfig(embed_dim=16, hidden_dim=32, input_size=64, device="cpu")
    )
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)["state_dict"]
    reloaded.net.load_state_dict(state)
    for name, param in trainer.net.model.named_parameters():
        assert torch.allclose(reloaded.net.state_dict()[name], param.detach(), atol=1e-6)
