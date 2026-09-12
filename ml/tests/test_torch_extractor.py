"""Tests for the pretrained-backbone embedding extractor.

These tests only run when ``RUN_TORCH_TESTS=1`` is set, since the first use
downloads the ImageNet-pretrained ResNet18 weights (~45 MB literal).
"""

from __future__ import annotations

import os

import numpy as np
import pytest

from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.identity import TorchEmbeddingExtractor

RUN_TORCH = os.environ.get("RUN_TORCH_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_TORCH,
    reason="set RUN_TORCH_TESTS=1 to run pretrained-backbone tests",
)


@pytest.fixture(scope="module")
def extractor() -> TorchEmbeddingExtractor:
    return TorchEmbeddingExtractor(backbone="resnet18")


def test_torch_extractor_empty_frame(extractor: TorchEmbeddingExtractor) -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    assert extractor.extract(frame, FrameDetections(0)) == []


def test_torch_extractor_produces_unit_norm_vectors(
    extractor: TorchEmbeddingExtractor,
) -> None:
    frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    detections = FrameDetections(
        frame_id=0,
        detections=[
            Detection(bbox=(100, 100, 80, 80), confidence=0.8),
            Detection(bbox=(400, 300, 60, 60), confidence=0.9),
        ],
    )
    embeddings = extractor.extract(frame, detections)
    assert len(embeddings) == 2
    for embedding in embeddings:
        norm = float(np.linalg.norm(embedding.vector))
        assert abs(norm - 1.0) < 1e-3
        assert embedding.track_id is None
        assert embedding.confidence > 0


def test_torch_extractor_similar_crops_embed_close() -> None:
    extractor = TorchEmbeddingExtractor(backbone="resnet18")
    # Two copies of the same crop should produce near-identical embeddings.
    base = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    a = extractor.extract(
        base,
        FrameDetections(0, [Detection(bbox=(100, 100, 80, 80), confidence=0.9)]),
    )[0]
    b = extractor.extract(
        base,
        FrameDetections(0, [Detection(bbox=(100, 100, 80, 80), confidence=0.9)]),
    )[0]
    similarity = float(np.dot(a.vector, b.vector))
    assert similarity > 0.99


def test_torch_extractor_ignores_track_id_tagging() -> None:
    extractor = TorchEmbeddingExtractor(backbone="resnet18")
    frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    fd = FrameDetections(
        frame_id=1,
        detections=[
            Detection(bbox=(50, 50, 40, 40), confidence=0.7, track_id=3),
        ],
    )
    embeddings = extractor.extract(frame, fd)
    assert embeddings[0].track_id == 3
