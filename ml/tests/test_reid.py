"""Tests for the mock re-identifier's track-chain identity numbering.

Identity numbers follow the tracking chain, not embedding clustering: every
brand-new track receives the next unused number unless it is a plausible
reappearance of a lost track, in which case it reuses the original number.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.detection import FrameDetections
from orchardvision_ml.detection.base import Detection
from orchardvision_ml.detection.mock import SCENARIO_ORCHARD, MockDetector
from orchardvision_ml.identity import Embedding, MockEmbeddingExtractor
from orchardvision_ml.reid import MockReIdentifier, ReIdentifier
from orchardvision_ml.tracking import MockTracker


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
    reid.step(2, [7], [])
    lost = reid.lost_tracks
    assert len(lost) == 1
    assert lost[0].track_id == 7
    assert lost[0].lost_at_frame == 2
    assert lost[0].recovered is False
    assert lost[0].identity_id is None


def test_duplicate_lost_register_only_once() -> None:
    reid = MockReIdentifier()
    reid.step(2, [7], [])
    reid.step(3, [7, 8], [])
    assert len(reid.lost_tracks) == 2


def test_new_tracks_receive_sequential_identity_numbers() -> None:
    reid = MockReIdentifier()
    extractor = _extractor()
    orange = _fruit_frame(120, 100, (0, 150, 210))
    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    second = _embed_fruit(extractor, _fruit_frame(320, 60, (120, 40, 60)), 0, (320, 60, 40, 40), 2)
    third = _embed_fruit(extractor, _fruit_frame(200, 240, (60, 90, 140)), 0, (200, 240, 40, 40), 3)

    reid.step(0, [], [first, second, third])

    assert reid.identity_for_track(1) == 1
    assert reid.identity_for_track(2) == 2
    assert reid.identity_for_track(3) == 3
    assert len(reid.events) == 0


def test_simultaneous_similar_fruits_never_share_identity() -> None:
    reid = MockReIdentifier(match_threshold=0.3)
    extractor = _extractor()
    orange = _fruit_frame(120, 100, (0, 150, 210))

    a = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    b = _embed_fruit(extractor, _fruit_frame(160, 100, (0, 150, 210)), 0, (160, 100, 40, 40), 2)

    events = reid.step(0, [], [a, b])

    assert events == []
    a_identity = reid.identity_for_track(1)
    b_identity = reid.identity_for_track(2)
    assert a_identity is not None
    assert b_identity is not None
    assert a_identity != b_identity


def test_recovery_emits_accepted_event_and_keeps_number() -> None:
    reid = MockReIdentifier()
    extractor = _extractor()
    orange = _fruit_frame(120, 100, (0, 150, 210))

    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    events = reid.step(0, [], [first])
    assert events == []
    identity_id = reid.identity_for_track(1)
    assert identity_id is not None

    reid.step(4, [1], [])

    recovered = _embed_fruit(
        extractor, _fruit_frame(124, 102, (0, 150, 210)), 5, (124, 102, 40, 40), 2
    )
    events = reid.step(5, [], [recovered])

    assert len(events) == 1
    event = events[0]
    assert event.accepted is True
    assert event.track_id == 2
    assert event.victim_track_id == 1
    assert event.identity_id == identity_id
    assert event.lost_frame_id == 4
    assert event.reappearance_frame_id == 5
    assert event.similarity >= reid.match_threshold
    assert event.identity_id in event.candidate_identity_ids
    assert len(event.candidate_scores) == len(event.candidate_identity_ids)
    for candidate_id, score in event.candidate_scores:
        assert candidate_id in event.candidate_identity_ids
        assert score >= reid.match_threshold
    assert reid.identity_for_track(2) == identity_id
    assert len(reid.events) == 1
    assert reid.lost_tracks[0].recovered is True


def test_new_fruit_after_loss_emits_no_event_but_gets_new_number() -> None:
    reid = MockReIdentifier()
    extractor = _extractor()
    orange = _fruit_frame(120, 100, (0, 150, 210))
    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    reid.step(0, [], [first])
    first_identity = reid.identity_for_track(1)
    reid.step(4, [1], [])

    red = _embed_fruit(extractor, _fruit_frame(520, 220, (0, 0, 230)), 5, (520, 220, 40, 40), 2)
    events = reid.step(5, [], [red])

    assert events == []
    assert reid.events == []
    assert reid.lost_tracks[0].recovered is False
    second_identity = reid.identity_for_track(2)
    assert second_identity is not None
    assert second_identity != first_identity


def test_reset_clears_state() -> None:
    reid = MockReIdentifier()
    reid.step(0, [1], [])
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
    orange = _fruit_frame(120, 100, (0, 150, 210))
    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    reid.step(0, [], [first])
    first_identity = reid.identity_for_track(1)
    reid.step(4, [1], [])

    far = _embed_fruit(extractor, _fruit_frame(320, 220, (0, 150, 210)), 5, (320, 220, 40, 40), 2)
    assert reid.step(5, [], [far]) == []
    assert reid.events == []
    assert reid.lost_tracks[0].recovered is False
    assert reid.identity_for_track(2) != first_identity

    near = _embed_fruit(extractor, _fruit_frame(124, 102, (0, 150, 210)), 6, (124, 102, 40, 40), 3)
    events = reid.step(6, [], [near])
    assert len(events) == 1
    assert events[0].victim_track_id == 1
    assert events[0].reappearance_frame_id == 6
    assert events[0].identity_id == first_identity


def test_motion_cap_grows_with_occlusion_gap() -> None:
    reid = MockReIdentifier(max_reid_displacement_px=50.0, max_speed_px_per_frame=20.0, top_k=5)
    extractor = _extractor()
    orange = _fruit_frame(120, 100, (0, 150, 210))
    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    reid.step(0, [], [first])
    reid.step(4, [1], [])

    far = _embed_fruit(extractor, _fruit_frame(300, 100, (0, 150, 210)), 5, (300, 100, 40, 40), 2)
    disp = 180.0
    assert disp > reid.max_reid_displacement_px + reid.max_speed_px_per_frame * 1
    assert reid.step(5, [], [far]) == []

    later = MockReIdentifier(max_reid_displacement_px=50.0, max_speed_px_per_frame=20.0, top_k=5)
    later.step(0, [], [first])
    later.step(4, [1], [])
    events = later.step(30, [], [far])
    assert len(events) == 1


def test_identity_without_pending_loss_does_not_block_lower_candidate() -> None:
    reid = MockReIdentifier(match_threshold=0.5, top_k=5)
    extractor = _extractor()
    orange = _fruit_frame(120, 100, (0, 150, 210))

    first = _embed_fruit(extractor, orange, 0, (120, 100, 40, 40), 1)
    reid.step(0, [], [first])
    a_identity = reid.identity_for_track(1)

    second = _embed_fruit(extractor, orange, 0, (200, 100, 40, 40), 5)
    reid.step(0, [], [second])
    b_identity = reid.identity_for_track(5)
    assert b_identity != a_identity

    reid.step(6, [5], [])

    reappears = _embed_fruit(extractor, orange, 7, (120, 100, 40, 40), 6)
    events = reid.step(7, [], [reappears])

    assert len(events) == 1
    assert events[0].identity_id == b_identity
    assert events[0].victim_track_id == 5
    assert events[0].similarity >= reid.match_threshold
    assert reid.identity_for_track(6) == b_identity
    assert reid.identity_for_track(1) == a_identity


def test_mock_scenario_counts_each_fruit_once_with_stable_numbering() -> None:
    """End-to-end chain numbering over the full 300-frame orchard scenario.

    The scenario contains exactly 7 distinct fruits with two absence gaps:
    fruit 5 disappears 140-175 and fruit 0 disappears 210-270. Each reappearing
    fruit must keep its original number, so the total identity count stays 7
    and two boxes can never show the same number at the same frame.
    """
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    detector = MockDetector(scenario=SCENARIO_ORCHARD)
    tracker = MockTracker(match_threshold=120.0, max_buffer=30)
    extractor = MockEmbeddingExtractor()
    reid = MockReIdentifier(match_threshold=0.6)
    max_assign_distance = 60.0

    identity_of_track: dict[int, int] = {}
    per_frame = {}

    for frame_id in range(300):
        frame_detections = detector.detect(frame, frame_id)
        result = tracker.update(frame_detections)
        assigned = []
        for det in frame_detections.detections:
            best_id: int | None = None
            best_distance: float | None = None
            cx, cy = det.center
            for track in result.active_tracks:
                if track.last_frame_id != result.frame_id:
                    continue
                bbox = track.current_bbox
                if bbox is None:
                    continue
                distance = (
                    (cx - (bbox[0] + bbox[2] / 2.0)) ** 2 + (cy - (bbox[1] + bbox[3] / 2.0)) ** 2
                ) ** 0.5
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_id = track.track_id
            track_id = (
                best_id
                if best_distance is not None and best_distance <= max_assign_distance
                else None
            )
            assigned.append(replace(det, track_id=track_id))

        reid.step(
            frame_id,
            result.lost_track_ids,
            extractor.extract(frame, replace(frame_detections, detections=assigned)),
        )

        per_frame[frame_id] = []
        for det in assigned:
            if det.track_id is None:
                continue
            identity_id = reid.identity_for_track(det.track_id)
            assert identity_id is not None, f"track {det.track_id} never got an identity"
            identity_of_track[det.track_id] = identity_id
            per_frame[frame_id].append((identity_id, det.track_id))

    assert len(set(identity_of_track.values())) == 7
    for frame_id, visible in per_frame.items():
        numbers = [identity for identity, _ in visible]
        assert len(numbers) == len(set(numbers)), f"duplicate numbers at frame {frame_id}"

    fruit5_chain = [track for identity, track in per_frame[176]]
    assert fruit5_chain
    fruit0_chain = [track for identity, track in per_frame[271]]
    assert fruit0_chain
