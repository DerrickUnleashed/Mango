"""Tests for the quality-aware identity memory."""

from __future__ import annotations

import numpy as np
import pytest

from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.identity import MockEmbeddingExtractor
from orchardvision_ml.memory import (
    IdentityMemory,
    MockIdentityMemory,
    quality_score,
)


def _fruit_frame(x: int, y: int, color: tuple[int, int, int] = (0, 150, 210)) -> np.ndarray:
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[y : y + 40, x : x + 40] = color
    return frame


def _extractor() -> MockEmbeddingExtractor:
    return MockEmbeddingExtractor()


def _observation(
    extractor: MockEmbeddingExtractor,
    frame: np.ndarray,
    frame_id: int,
    x: int,
    y: int,
    confidence: float = 0.9,
    track_id: int | None = None,
):
    det = Detection(bbox=(float(x), float(y), 40.0, 40.0), confidence=confidence, track_id=track_id)
    return extractor.extract(frame, FrameDetections(frame_id=frame_id, detections=[det]))[0]


def test_first_observation_creates_identity() -> None:
    memory = MockIdentityMemory()
    frame = _fruit_frame(120, 100)
    identity = memory.update(_observation(_extractor(), frame, 0, 120, 100))
    assert identity is not None
    assert identity.identity_id == 1
    assert identity.observation_count == 1


def test_similar_observation_updates_existing_identity() -> None:
    memory = MockIdentityMemory()
    extractor = _extractor()
    frame = _fruit_frame(120, 100)
    first = memory.update(_observation(extractor, frame, 0, 120, 100))
    assert first is not None

    # A later, nearly identical appearance of the same fruit
    second = memory.update(_observation(extractor, _fruit_frame(124, 102), 5, 124, 102, track_id=7))
    assert second is not None
    assert second.identity_id == first.identity_id
    assert second.observation_count == 2
    assert len(memory.identities) == 1
    assert second.last_track_id == 7
    assert second.is_confident is False  # only 2 observations


def test_distinct_fruit_creates_new_identity() -> None:
    memory = MockIdentityMemory()
    extractor = _extractor()
    orange = _fruit_frame(120, 100, (0, 150, 210))
    red = _fruit_frame(500, 220, (0, 0, 230))
    a = memory.update(_observation(extractor, orange, 0, 120, 100))
    b = memory.update(_observation(extractor, red, 1, 500, 220))
    assert a is not None and b is not None
    assert b.identity_id != a.identity_id
    assert len(memory.identities) == 2


def test_low_quality_observation_is_suppressed() -> None:
    memory = MockIdentityMemory(min_quality=0.5)
    extractor = _extractor()
    frame = _fruit_frame(120, 100)
    identity = memory.update(_observation(extractor, frame, 0, 120, 100, confidence=0.2))
    assert identity is None
    assert memory.identities == []


def test_occlusion_penalizes_quality() -> None:
    assert quality_score(0.9, is_occluded=False) > quality_score(0.9, is_occluded=True)
    assert quality_score(0.9, is_occluded=True) < 0.9


def test_query_ranks_best_match_first() -> None:
    memory = MockIdentityMemory()
    extractor = _extractor()
    orange = _fruit_frame(120, 100, (0, 150, 210))
    red = _fruit_frame(500, 220, (0, 0, 230))
    memory.update(_observation(extractor, orange, 0, 120, 100))
    memory.update(_observation(extractor, red, 1, 500, 220))

    ranked = memory.query(_observation(extractor, _fruit_frame(122, 100), 2, 122, 100))
    assert len(ranked) == 2
    assert ranked[0][0].identity_id == 1
    assert ranked[0][1] > ranked[1][1]


def test_prototype_stays_unit_norm() -> None:
    memory = MockIdentityMemory()
    extractor = _extractor()
    frame = _fruit_frame(120, 100)
    for frame_id in range(3):
        identity = _observation(extractor, frame, frame_id, 120 + frame_id, 100)
        stored = memory.update(identity)
        assert stored is not None
        assert abs(np.linalg.norm(stored.prototype) - 1.0) < 1e-5


def test_memory_is_deterministic() -> None:
    def run() -> list[int]:
        memory = MockIdentityMemory()
        extractor = _extractor()
        ids: list[int] = []
        for frame_id, (x, y, color) in enumerate(
            [(120, 100, (0, 150, 210)), (500, 220, (0, 0, 230))]
        ):
            identity = memory.update(
                _observation(extractor, _fruit_frame(x, y, color), frame_id, x, y)
            )
            assert identity is not None
            ids.append(identity.identity_id)
        return ids

    assert run() == run()


def test_memory_interface_enforces_update() -> None:
    class BrokenMemory(IdentityMemory):
        @property
        def name(self) -> str:
            return "broken"

    with pytest.raises(TypeError):
        _ = BrokenMemory()  # type: ignore[misc]  # noqa: F841, S106
