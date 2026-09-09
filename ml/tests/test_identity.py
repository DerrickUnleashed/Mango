"""Tests for identity embedding extractors."""

from __future__ import annotations

import numpy as np
import pytest

from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.identity import (
    EMBEDDING_DIM,
    EmbeddingExtractor,
    MockEmbeddingExtractor,
    cosine_similarity,
)


def _frame(seed: int, size: tuple[int, int] = (360, 640)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(size[0], size[1], 3), dtype=np.uint8)


def _dets(frame_id: int, *boxes: tuple) -> FrameDetections:
    return FrameDetections(
        frame_id=frame_id,
        detections=[Detection(bbox=b, confidence=0.8) for b in boxes],
    )


def test_extractor_is_deterministic() -> None:
    extractor = MockEmbeddingExtractor()
    frame = _frame(7)
    a = extractor.extract(frame, _dets(0, (100, 100, 40, 40)))
    b = extractor.extract(frame, _dets(0, (100, 100, 40, 40)))
    assert len(a) == 1 and len(b) == 1
    np.testing.assert_array_almost_equal(a[0].vector, b[0].vector)


def test_embeddings_are_unit_norm() -> None:
    extractor = MockEmbeddingExtractor()
    frame = _frame(3)
    embeddings = extractor.extract(frame, _dets(0, (100, 100, 40, 40), (500, 200, 40, 40)))
    assert len(embeddings) == 2
    for e in embeddings:
        assert e.dimension == EMBEDDING_DIM
        assert abs(np.linalg.norm(e.vector) - 1.0) < 1e-5


def test_same_crop_embeds_similarly() -> None:
    extractor = MockEmbeddingExtractor()
    frame = _frame(11)
    # Identical detection of the same fruit region in a later frame
    a = extractor.extract(frame, _dets(0, (100, 100, 40, 40)))[0]
    b = extractor.extract(frame, _dets(5, (100, 100, 40, 40)))[0]
    assert cosine_similarity(a.vector, b.vector) > 0.98


def test_different_regions_embed_less_similarly() -> None:
    extractor = MockEmbeddingExtractor()
    frame = _frame(11)
    a = extractor.extract(frame, _dets(0, (100, 100, 40, 40)))[0]
    b = extractor.extract(frame, _dets(0, (520, 220, 40, 40)))[0]
    assert cosine_similarity(a.vector, b.vector) < 0.99


def test_occlusion_flag_from_confidence() -> None:
    extractor = MockEmbeddingExtractor()
    frame = _frame(5)
    low = FrameDetections(
        frame_id=0, detections=[Detection(bbox=(100, 100, 40, 40), confidence=0.2)]
    )
    high = FrameDetections(
        frame_id=0, detections=[Detection(bbox=(100, 100, 40, 40), confidence=0.9)]
    )
    assert extractor.extract(frame, low)[0].is_occluded is True
    assert extractor.extract(frame, high)[0].is_occluded is False


def test_track_ids_carried_into_embeddings() -> None:
    extractor = MockEmbeddingExtractor()
    frame = _frame(2)
    det = Detection(bbox=(100, 100, 40, 40), confidence=0.8, track_id=42)
    embeddings = extractor.extract(frame, FrameDetections(frame_id=3, detections=[det]))
    assert embeddings[0].track_id == 42
    assert embeddings[0].frame_id == 3


def test_embedder_interface_enforces_extract_method() -> None:
    class BrokenExtractor(EmbeddingExtractor):
        @property
        def name(self) -> str:
            return "broken"

    with pytest.raises(TypeError):
        _ = BrokenExtractor()  # type: ignore[misc]  # noqa: F841, S106
