"""Tests for the trained-identity ``Embedder`` (Stage D swap-in).

Gated behind ``RUN_TORCH_TESTS=1``: training the checkpoint needs the torch
backend, and the first run downloads the ImageNet-pretrained backbone.
"""

from __future__ import annotations

import os

import numpy as np
import pytest
import torch

from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.identity import Embedder
from orchardvision_ml.identity.dataset import TrackletDataset, TrackletPartitioner, TrackObservation
from orchardvision_ml.identity.embedder import Embedder as EmbedderClass
from orchardvision_ml.identity.torch_trainer import (
    TorchContrastiveTrainer,
    TorchTrainerConfig,
)
from orchardvision_ml.identity.training import PairOptions

RUN_TORCH = os.environ.get("RUN_TORCH_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_TORCH,
    reason="set RUN_TORCH_TESTS=1 to run torch trainer tests",
)


def _build_checkpoint(tmp_path) -> str:
    """Train a tiny model so the swap-in loads real, functional weights."""
    observations = []
    for track_id, x in zip((1, 2), (100.0, 600.0), strict=True):
        for frame_id in (0, 2):
            observations.append(
                TrackObservation(
                    track_id=track_id,
                    frame_id=frame_id,
                    bbox=(x, 100.0, 30.0, 30.0),
                    confidence=0.9,
                    source_id="cam0",
                )
            )
    cache: dict[tuple[str, int], np.ndarray] = {}
    colors = {1: (220, 60, 60), 2: (60, 120, 220)}

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

    dataset = TrackletDataset(
        observations,
        pair_options=PairOptions(max_frames_apart=8, min_center_distance=60.0),
        partitioner=TrackletPartitioner(min_sub_length=1),
    )
    trainer = TorchContrastiveTrainer(TorchTrainerConfig(epochs=2, batch_size=2))
    trainer.train(dataset.build_pairs(), provider)
    return trainer.save(str(tmp_path / "embedder.pt"))


def test_embedder_loads_checkpoint_and_produces_unit_norm_vectors(tmp_path) -> None:
    path = _build_checkpoint(tmp_path)
    embedder = Embedder(path)

    dets = FrameDetections(
        frame_id=2,
        detections=[
            Detection(track_id=1, bbox=(100.0, 100.0, 30.0, 30.0), confidence=0.9),
            Detection(track_id=2, bbox=(600.0, 100.0, 30.0, 30.0), confidence=0.9),
        ],
    )
    frame = np.full((480, 640, 3), 30, dtype=np.uint8)
    frame[100:130, 100:130] = (220, 60, 60)
    frame[100:130, 600:630] = (60, 120, 220)

    embeddings = embedder.extract(frame, dets)
    assert len(embeddings) == 2
    assert embeddings[0].track_id == 1 and embeddings[1].track_id == 2
    assert all(np.isclose(np.linalg.norm(emb.vector), 1.0, atol=1e-4) for emb in embeddings)


def test_embedder_empty_detections_returns_empty(tmp_path) -> None:
    path = _build_checkpoint(tmp_path)
    embedder = Embedder(path)
    frame = np.full((480, 640, 3), 30, dtype=np.uint8)
    embeddings = embedder.extract(frame, FrameDetections(frame_id=0, detections=[]))
    assert embeddings == []


def test_embedder_is_public_extractor_interface(tmp_path) -> None:
    path = _build_checkpoint(tmp_path)
    embedder: EmbedderClass = Embedder(path)
    assert embedder.name.startswith("trained-")
    assert "state_dict" in torch.load(path, weights_only=False)
