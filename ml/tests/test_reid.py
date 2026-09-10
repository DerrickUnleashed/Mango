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


def test_embeddings_carry_bbox_for_motion_gating() -> None:
    emb = _embed_fruit(
        _extractor(), _fruit_frame(120, 100, (0, 150, 210)), 0, (120, 100, 40, 40), 1
    )
    assert emb.bbox == (120, 100, 40, 40)


def test_recovery_gated_by_motion_displacement() -> None:
    reid = MockReIdentifier(max_reid_displacement_px=50.0, max_speed_px_per_frame=0.0, top_k=5)
    extractor = _extractor()
    memory = _memory()
    orange = _fruit_frame(120, 100, (0, 150, 210))
    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    memory.update(first)
    reid.step(0, [], [first], memory)
    reid.step(4, [1], [], memory)

    far = _embed_fruit(extractor, _fruit_frame(320, 220, (0, 150, 210)), 5, (320, 220, 40, 40), 2)
    assert reid.step(5, [], [far], memory) == []
    assert reid.events == []
    assert reid.lost_tracks[0].recovered is False

    near = _embed_fruit(extractor, _fruit_frame(124, 102, (0, 150, 210)), 6, (124, 102, 40, 40), 3)
    events = reid.step(6, [], [near], memory)
    assert len(events) == 1
    assert events[0].victim_track_id == 1
    assert events[0].reappearance_frame_id == 6


def test_motion_cap_grows_with_occlusion_gap() -> None:
    reid = MockReIdentifier(max_reid_displacement_px=50.0, max_speed_px_per_frame=20.0, top_k=5)
    extractor = _extractor()
    memory = _memory()
    orange = _fruit_frame(120, 100, (0, 150, 210))
    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    memory.update(first)
    reid.step(0, [], [first], memory)
    reid.step(4, [1], [], memory)

    far = _embed_fruit(extractor, _fruit_frame(300, 100, (0, 150, 210)), 5, (300, 100, 40, 40), 2)
    disp = 180.0
    assert disp > reid.max_reid_displacement_px + reid.max_speed_px_per_frame * 1
    assert reid.step(5, [], [far], memory) == []

    later = MockReIdentifier(max_reid_displacement_px=50.0, max_speed_px_per_frame=20.0, top_k=5)
    later.step(0, [], [first], memory)
    later.step(4, [1], [], memory)
    events = later.step(30, [], [far], memory)
    assert len(events) == 1


def test_identity_without_pending_loss_does_not_block_lower_candidate() -> None:
    reid = MockReIdentifier(match_threshold=0.5, top_k=5)
    memory = MockIdentityMemory(match_threshold=0.95)
    extractor = _extractor()
    orange = _fruit_frame(120, 100, (0, 150, 210))

    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    memory.update(first)
    reid.step(0, [], [first], memory)
    a_identity = memory.query(first, top_k=1)[0][0].identity_id

    second = _embed_fruit(extractor, orange, 0, (200, 100, 40, 40), 5)
    memory.update(second)
    reid.step(0, [], [second], memory)
    b_identity = memory.query(second, top_k=1)[0][0].identity_id
    assert b_identity != a_identity

    reid.step(6, [5], [], memory)

    reappears = _embed_fruit(extractor, orange, 7, (120, 100, 40, 40), 6)
    events = reid.step(7, [], [reappears], memory)

    assert len(events) == 1
    assert events[0].identity_id == b_identity
    assert events[0].victim_track_id == 5
    assert events[0].similarity >= reid.match_threshold
