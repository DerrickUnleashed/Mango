"""Tests for tracking interfaces and implementations."""

from __future__ import annotations

from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.tracking import (
    ByteTrackAdapter,
    MockTracker,
    Tracker,
    associate_by_center_distance,
)


def _frame(
    frame_id: int, *box_confs: tuple[tuple[float, float, float, float], float]
) -> FrameDetections:
    return FrameDetections(
        frame_id=frame_id,
        detections=[Detection(bbox=bc[0], confidence=bc[1]) for bc in box_confs],
    )


def test_associate_by_center_distance_basic() -> None:
    dets = [Detection(bbox=(0, 0, 10, 10), confidence=0.9)]
    from orchardvision_ml.tracking import Track

    track = Track(track_id=1)
    track.update(0, Detection(bbox=(0, 0, 10, 10), confidence=0.9))
    matches, unmatched_det, unmatched_trk = associate_by_center_distance(
        dets, [track], threshold=20.0
    )
    assert matches == [(0, 0)]
    assert unmatched_det == []
    assert unmatched_trk == []


def test_mock_tracker_persists_ids_across_frames() -> None:
    tracker = MockTracker()
    # Two stable fruits
    for frame_id in range(0, 10):
        result = tracker.update(
            _frame(
                frame_id,
                ((100, 100, 30, 30), 0.9),
                ((500, 300, 30, 30), 0.8),
            )
        )
    assert result.total_tracks == 2
    ids = {t.track_id for t in result.active_tracks}
    assert len(ids) == 2


def test_mock_tracker_new_and_lost_track_lifecycle() -> None:
    tracker = MockTracker(max_buffer=3)
    result = tracker.update(_frame(0, ((100, 100, 30, 30), 0.9)))
    assert result.new_track_ids
    track_id = result.active_tracks[0].track_id

    # Fruit disappears; the track must be reported lost after `max_buffer` frames
    lost_seen = False
    for _ in range(4):
        result = tracker.update(_frame(1))
        if track_id in result.lost_track_ids:
            lost_seen = True
    assert lost_seen
    assert track_id not in {t.track_id for t in result.active_tracks}

    # A new fruit appears later — gets a fresh id
    later = tracker.update(_frame(10, ((120, 120, 30, 30), 0.9)))
    assert track_id not in {t.track_id for t in later.active_tracks}


def test_bytetrack_adapter_tracks_stable_fruit() -> None:
    tracker = ByteTrackAdapter()
    for frame_id in range(0, 15):
        x = 100 + frame_id * 3
        result = tracker.update(_frame(frame_id, ((x, 100, 30, 30), 0.8)))
    assert result.total_tracks >= 1
    tracks = result.active_tracks
    assert tracks
    # Track should have accumulated observations across all frames
    assert tracks[0].length >= 14


def test_bytetrack_adapter_recovers_after_short_gap() -> None:
    tracker = ByteTrackAdapter(buffer_size=10)
    result = None
    for frame_id in range(0, 5):
        result = tracker.update(_frame(frame_id, ((100 + frame_id, 100, 30, 30), 0.8)))
    original_id = result.active_tracks[0].track_id
    # Occlusion: fruit missing for a few frames, then reappears
    for frame_id in range(5, 9):
        tracker.update(_frame(frame_id))
    result = tracker.update(_frame(9, ((110, 100, 30, 30), 0.7)))
    assert any(t.track_id == original_id for t in result.active_tracks)


def test_bytetrack_adapter_gap_longer_than_buffer_creates_new_id() -> None:
    tracker = ByteTrackAdapter(buffer_size=3)
    result = None
    for frame_id in range(0, 3):
        result = tracker.update(_frame(frame_id, ((100 + frame_id, 100, 30, 30), 0.8)))
    original_id = result.active_tracks[0].track_id
    for frame_id in range(3, 10):
        tracker.update(_frame(frame_id))
    result = tracker.update(_frame(10, ((110, 100, 30, 30), 0.7)))
    assert all(t.track_id != original_id for t in result.active_tracks)


def test_bytetrack_adapter_high_and_low_confidence_association() -> None:
    tracker = ByteTrackAdapter(high_threshold=0.5, buffer_size=20)
    # Track a fruit at high confidence
    result = tracker.update(_frame(0, ((200, 200, 30, 30), 0.9)))
    tid = result.active_tracks[0].track_id
    # Next frame: same place but low confidence (occluded-ish) — must reconnect
    result = tracker.update(_frame(1, ((205, 200, 30, 30), 0.3)))
    assert any(t.track_id == tid for t in result.active_tracks)


def test_kalman_yields_sane_estimate() -> None:
    from orchardvision_ml.tracking import KalmanBoxFilter, to_tlwh, to_xyah

    kf = KalmanBoxFilter()
    kf.initiate(to_xyah((100, 100, 30, 30)))
    kf.predict()
    est = to_tlwh(kf.get_estimate_xyah())
    x, y, w, h = est
    assert abs(x - 100) < 10
    assert abs(y - 100) < 10
    assert 20 < w < 40
    assert 20 < h < 40

    # Update with a nearby measurement
    kf.update(to_xyah((110, 110, 30, 30)))
    est2 = to_tlwh(kf.get_estimate_xyah())
    assert abs(est2[0] - 110) < 15


def test_tracker_name_properties() -> None:
    assert MockTracker().name == "mock-tracker"
    assert ByteTrackAdapter().name == "bytetrack-adapter"


def test_track_point_timestamps_and_confidence() -> None:
    from orchardvision_ml.tracking import Track

    track = Track(track_id=1)
    track.update(0, Detection(bbox=(0, 0, 10, 10), confidence=0.7))
    track.update(1, Detection(bbox=(20, 20, 10, 10), confidence=0.9))
    assert track.length == 2
    assert track.last_frame_id == 1
    assert track.points[0].frame_id == 0
    assert abs(track.points[1].confidence - 0.9) < 1e-9
    assert 0.79 < track.average_confidence < 0.81
    assert track.current_bbox == (20, 20, 10, 10)


def test_tracker_interface_enforces_update_method() -> None:
    class BrokenTracker(Tracker):
        @property
        def name(self) -> str:
            return "broken"

    import pytest

    with pytest.raises(TypeError):
        _ = BrokenTracker()  # type: ignore[misc]  # noqa: F841, S106
