"""Tests for the mock re-identifier."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.detection import FrameDetections
from orchardvision_ml.detection.base import Detection
from orchardvision_ml.identity import Embedding, MockEmbeddingExtractor
from orchardvision_ml.memory import MockIdentityMemory
from orchardvision_ml.reid import MockReIdentifier, ReIdentifier


def _fruit_frame(x: int, y: int, color: tuple[int, int, int]) -> NDArray[np.uint8]:
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[y : y + 40, x : x + 40] = color
    return frame


def _det(
    track_id: int, bbox: tuple[float, float, float, float], confidence: float = 0.9
) -> Detection:
    return Detection(bbox=bbox, confidence=confidence, class_label="fruit", track_id=track_id)


def _extractor() -> MockEmbeddingExtractor:
    return MockEmbeddingExtractor()


def _memory() -> MockIdentityMemory:
    return MockIdentityMemory()


def _embed_fruit(
    extractor: MockEmbeddingExtractor,
    frame: NDArray[np.uint8],
    frame_id: int,
    bbox: tuple[float, float, float, float],
    track_id: int,
) -> Embedding:
    fd = FrameDetections(frame_id=frame_id, detections=[_det(track_id, bbox)])
    return extractor.extract(frame, fd)[0]


def test_reidentifier_interface_importable() -> None:
    assert issubclass(MockReIdentifier, ReIdentifier)
    assert MockReIdentifier().name == "MockReIdentifier"


def test_lost_track_is_registered() -> None:
    reid = MockReIdentifier()
    reid.step(2, [7], [], _memory())
    lost = reid.lost_tracks
    assert len(lost) == 1
    assert lost[0].track_id == 7
    assert lost[0].lost_at_frame == 2
    assert lost[0].recovered is False


def test_duplicate_lost_register_only_once() -> None:
    reid = MockReIdentifier()
    reid.step(2, [7], [], _memory())
    reid.step(3, [7, 8], [], _memory())
    assert len(reid.lost_tracks) == 2


def test_recovery_emits_accepted_event() -> None:
    reid = MockReIdentifier()
    extractor = _extractor()
    memory = _memory()
    orange = _fruit_frame(120, 100, (0, 150, 210))

    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    ret = memory.update(first)
    assert ret is not None
    identity_id = ret.identity_id

    reid.step(0, [], [first], memory)
    reid.step(4, [1], [], memory)

    recovered = _embed_fruit(
        extractor, _fruit_frame(124, 102, (0, 150, 210)), 5, (124, 102, 40, 40), 2
    )
    events = reid.step(5, [], [recovered], memory)

    assert len(events) == 1
    event = events[0]
    assert event.accepted is True
    assert event.track_id == 2
    assert event.victim_track_id == 1
    assert event.identity_id == identity_id
    assert event.lost_frame_id == 4
    assert event.reappearance_frame_id == 5
    assert event.similarity >= reid.match_threshold
    assert len(reid.events) == 1
    assert reid.lost_tracks[0].recovered is True


def test_new_fruit_after_loss_emits_no_event() -> None:
    reid = MockReIdentifier()
    extractor = _extractor()
    memory = _memory()
    orange = _fruit_frame(120, 100, (0, 150, 210))
    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    memory.update(first)
    reid.step(0, [], [first], memory)
    reid.step(4, [1], [], memory)

    red = _embed_fruit(extractor, _fruit_frame(520, 220, (0, 0, 230)), 5, (520, 220, 40, 40), 2)
    events = reid.step(5, [], [red], memory)
    assert events == []
    assert reid.events == []
    assert reid.lost_tracks[0].recovered is False


def test_reset_clears_state() -> None:
    reid = MockReIdentifier()
    reid.step(0, [1], [], _memory())
    reid.reset()
    assert reid.events == []
    assert reid.lost_tracks == []
