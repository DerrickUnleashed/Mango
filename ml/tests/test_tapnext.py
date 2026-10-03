"""Tests for the TAPNext++ point-enhanced tracker adapter.

Most tests inject a fake model object that mimics the
``track_frame(frame, query_points_xy=None, state=None)`` contract, so they run
without torch (important: the CI backend job skips torch-gated tests). The
REAL model wrapper is exercised only under ``RUN_TORCH_TESTS=1`` at the bottom
of this file with a tiny untrained TAPNext to keep it fast.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import numpy as np
import pytest

from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.tracking import TAPNextTracker
from orchardvision_ml.tracking.tapnext_tracker import _greedy_match_by_distance

H, W = 720, 1280


def _det(cx: float, cy: float, size: float = 40.0, conf: float = 0.9) -> Detection:
    return Detection((cx - size / 2, cy - size / 2, size, size), conf)


def _frame() -> np.ndarray:
    return np.zeros((H, W, 3), np.uint8)


Method = Callable[[int, list[list[float]]], tuple[list[list[float]], list[bool]]]


class FakeModel:
    """Deterministic stand-in for the TAPNext++ wrapper.

    ``behavior(n_queries, seeds)`` returns ``(offsets, visible)``: each call,
    the model reports the seed positions (plus the offsets) as tracked points
    for all live queries. A ``query_points_xy`` call starts a fresh session
    with exactly those rows — used for the initial seed and for rebootstrap
    re-seeds — while a state-only call keeps the current rows, mirroring the
    real model's per-session fixed query set.
    """

    def __init__(self, behavior: Method | None = None) -> None:
        self.seeds: list[list[float]] = []
        self.calls: list[int] = []
        self._behavior = behavior or (lambda n, seeds: ([[0.0, 0.0]] * n, [True] * n))

    def track_frame(self, frame, query_points_xy=None, state=None):
        if query_points_xy is not None:
            self.seeds = [[float(p[0]), float(p[1])] for p in query_points_xy]
        offsets, visible = self._behavior(len(self.seeds), self.seeds)
        positions = np.asarray(
            [[sx + ox, sy + oy] for (sx, sy), (ox, oy) in zip(self.seeds, offsets, strict=True)],
            np.float32,
        )
        self.calls.append(len(self.seeds))
        return positions, np.asarray(visible, bool), object()


# --- unit: greedy distance matcher -------------------------------------------


def test_greedy_match_pairs_by_distance() -> None:
    det_points = np.asarray([[0.0, 0.0], [10.0, 0.0]])
    cand_points = np.asarray([[0.0, 0.0], [11.0, 0.0]])
    matches, unmatched_det, unmatched_cand = _greedy_match_by_distance(
        det_points, cand_points, threshold=2.0
    )
    assert len(matches) == 2
    assert unmatched_det == []
    assert unmatched_cand == []


def test_greedy_match_threshold_blocks_far_pairs() -> None:
    matches, unmatched_det, unmatched_cand = _greedy_match_by_distance(
        np.asarray([[0.0, 0.0]]),
        np.asarray([[0.0, 10.0]]),
        threshold=5.0,
    )
    assert matches == []
    assert unmatched_det == [0]
    assert unmatched_cand == [0]


def test_greedy_match_winner_takes_all() -> None:
    matches, _, _ = _greedy_match_by_distance(
        np.asarray([[0.0, 0.0], [1.0, 0.0]]),
        np.asarray([[0.0, 0.0]]),
        threshold=5.0,
    )
    # The nearer detection wins the single candidate.
    assert matches == [(0, 0)]


def test_greedy_match_handles_empty_sides() -> None:
    empty = np.asarray([], np.float64)
    matches, unmatched_det, unmatched_cand = _greedy_match_by_distance(
        empty, np.asarray([[0.0, 0.0]]), threshold=5.0
    )
    assert matches == []
    assert unmatched_det == []
    assert unmatched_cand == [0]

    matches, unmatched_det, unmatched_cand = _greedy_match_by_distance(
        np.asarray([[0.0, 0.0]]), empty, threshold=5.0
    )
    assert matches == []
    assert unmatched_det == [0]
    assert unmatched_cand == []


# --- tracker lifecycle --------------------------------------------------------


def test_first_frame_seeds_queries_and_creates_tracks() -> None:
    model = FakeModel()
    tracker = TAPNextTracker(model=model, match_threshold_px=120)
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(0, [_det(100, 100), _det(600, 300)]))
    assert result.total_tracks == 2
    assert result.new_track_ids == [1, 2]
    assert tracker._query_track_ids == [1, 2]
    assert len(model.calls) == 1
    assert model.calls[-1] == 2


def test_continuous_fruit_keeps_same_track() -> None:
    model = FakeModel()
    tracker = TAPNextTracker(model=model, match_threshold_px=120)
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(0, [_det(100, 100)]))
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(1, [_det(104, 98)]))
    assert result.total_tracks == 1
    assert result.new_track_ids == []
    track = tracker._tracks[1]
    assert track.length == 2
    # The point comes from the model, not the detection bbox.
    assert tracker._last_points[1] == (100.0, 100.0)


def test_mid_stream_fruit_is_position_only() -> None:
    """A fruit first seen after the seed frame gets no query row."""
    model = FakeModel()
    tracker = TAPNextTracker(model=model, match_threshold_px=120)
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(0, [_det(100, 100)]))
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(1, [_det(800, 500)]))
    assert result.total_tracks == 2
    assert result.new_track_ids == [2]
    assert tracker._query_track_ids == [1]
    # The model is stepped with state only; no new query points are sent.
    assert len(model.calls) == 2
    assert model.seeds == [[100.0, 100.0]]
    # Its last known point is the detection centre, so a reappearance nearby
    # associates to the same track.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(2, [_det(802, 502)]))
    assert result.total_tracks == 2
    assert result.new_track_ids == []
    assert tracker._query_track_ids == [1]
    assert tracker._tracks[2].length == 2


def test_update_requires_frame_first() -> None:
    tracker = TAPNextTracker(model=FakeModel())
    with pytest.raises(RuntimeError, match="update_frame"):
        tracker.update(FrameDetections(0, [_det(100, 100)]))


def test_tracker_requires_checkpoint_or_model() -> None:
    tracker = TAPNextTracker()
    tracker.update_frame(_frame())
    with pytest.raises(ValueError, match="checkpoint_path"):
        tracker.update(FrameDetections(0, [_det(100, 100)]))


def test_empty_frame_before_seed_is_a_noop() -> None:
    model = FakeModel()
    tracker = TAPNextTracker(model=model, match_threshold_px=120)
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(0, []))
    assert result.total_tracks == 0
    assert model.calls == []
    # A later seed can still initialise the model normally.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(1, [_det(100, 100)]))
    assert result.total_tracks == 1
    assert tracker._query_track_ids == [1]


# --- occlusion and retirement -------------------------------------------------


def test_occlusion_buffers_then_reasserts_same_track() -> None:
    calls = {"n": 0}

    def behavior(_n: int, _seeds: list[list[float]]):
        calls["n"] += 1
        if calls["n"] == 2:
            return [[0.0, 0.0]], [False]  # fruit occluded
        if calls["n"] == 3:
            return [[60.0, 40.0]], [True]  # reappeared up-right
        return [[0.0, 0.0]], [True]

    model = FakeModel(behavior)
    tracker = TAPNextTracker(model=model, match_threshold_px=120)
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(0, [_det(100, 100)]))
    # Occluded frame: no detection -> no new track, still active.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(1, []))
    assert result.total_tracks == 1
    assert result.new_track_ids == []
    assert 1 not in result.lost_track_ids
    assert tracker._frames_since_match[1] == 1
    # Reappearance near the re-detected point keeps the track id.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(2, [_det(160, 140)]))
    assert result.total_tracks == 1
    assert result.new_track_ids == []
    assert tracker._frames_since_match[1] == 0
    assert tracker._tracks[1].length == 2


def test_lost_track_retired_after_buffer_expires() -> None:
    model = FakeModel()
    tracker = TAPNextTracker(model=model, match_threshold_px=120, buffer_size=2)
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(0, [_det(100, 100)]))
    for frame_id in (1, 2, 3):
        tracker.update_frame(_frame())
        result = tracker.update(FrameDetections(frame_id, []))
    assert 1 in result.lost_track_ids
    assert result.total_tracks == 0
    assert result.active_tracks == []
    assert tracker._query_track_ids == [1]  # retired track keeps its row
    # Once retired it stays gone.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(4, []))
    assert result.lost_track_ids == []
    assert result.total_tracks == 0


# --- query capacity fallback --------------------------------------------------


def test_query_cap_falls_back_to_buffer_only_tracks() -> None:
    model = FakeModel()
    tracker = TAPNextTracker(model=model, match_threshold_px=120, max_query_points=1)
    tracker.update_frame(_frame())
    # Two far fruits on frame 0: only one can claim a query row.
    result = tracker.update(FrameDetections(0, [_det(100, 100), _det(600, 300)]))
    assert result.total_tracks == 2
    assert result.new_track_ids == [1, 2]
    assert tracker._query_track_ids == [1]
    assert len(model.calls) == 1
    assert model.calls[-1] == 1
    # A third fruit arrives and the cap is still full: buffer-only again.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(1, [_det(800, 500)]))
    assert result.total_tracks == 3
    assert result.new_track_ids == [3]
    assert tracker._query_track_ids == [1]
    assert len(model.calls) == 2
    # A detection over a buffer-only track's last point associates, not re-seeds.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(2, [_det(602, 302)]))
    assert result.total_tracks == 3
    assert result.new_track_ids == []
    assert tracker._query_track_ids == [1]


# --- rebootstrap (mid-stream query growth) -----------------------------------


def test_rebootstrap_grows_query_set_mid_stream() -> None:
    model = FakeModel()
    tracker = TAPNextTracker(model=model, match_threshold_px=120, rebootstrap_interval=3)
    # Frame 0 seeds the model with one fruit.
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(0, [_det(100, 100)]))
    assert tracker._query_track_ids == [1]
    assert model.calls == [1]
    # A fruit appears mid-stream: its query waits (interval 3, origin 0), but
    # the track exists and is position-only meanwhile.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(1, [_det(600, 300)]))
    assert result.total_tracks == 2
    assert result.new_track_ids == [2]
    assert tracker._query_track_ids == [1]
    assert tracker._pending_queries == [2]
    assert model.calls == [1, 1]
    # Frame 2 still advances state only (interval not reached).
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(2, []))
    assert tracker._pending_queries == [2]
    assert model.calls == [1, 1, 1]
    # Frame 3: eligible -> re-seed with both queries and replay frames 0..3.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(3, []))
    assert tracker._query_track_ids == [1, 2]
    assert tracker._pending_queries == []
    assert tracker._bootstrap_frame_id == 3
    # Fresh seed (2 rows) + replay of frames 1,2,3 (2 rows each).
    assert model.calls == [1, 1, 1, 2, 2, 2, 2]
    assert len(model.seeds) == 2
    # The late fruit continues as a real query after the reboot.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(4, [_det(600, 300)]))
    assert result.total_tracks == 2
    assert result.new_track_ids == []
    assert tracker._query_track_ids == [1, 2]
    assert tracker._tracks[2].length == 2  # birth frame + this match
    assert model.calls[-1] == 2


def test_position_only_when_rebootstrap_disabled() -> None:
    """Default (interval 0) keeps the fixed set behaviour, no deferred rows."""
    model = FakeModel()
    tracker = TAPNextTracker(model=model, match_threshold_px=120)
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(0, [_det(100, 100)]))
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(1, [_det(600, 300)]))
    assert result.total_tracks == 2
    assert tracker._query_track_ids == [1]
    assert tracker._pending_queries == []
    assert not tracker._maybe_rebootstrap(model, 1)


def test_rebootstrap_respects_query_capacity() -> None:
    model = FakeModel()
    tracker = TAPNextTracker(
        model=model, match_threshold_px=120, max_query_points=2, rebootstrap_interval=2
    )
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(0, [_det(100, 100), _det(300, 200)]))
    assert tracker._query_track_ids == [1, 2]
    # Capacity full -> third fruit cannot even be deferred to a rebootstrap.
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(1, [_det(600, 300)]))
    assert tracker._pending_queries == []
    assert tracker._query_track_ids == [1, 2]
    # No pending, so no reboot ever triggers.
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(2, []))
    assert tracker._query_track_ids == [1, 2]


def test_retired_pending_track_not_reboot_seeded() -> None:
    """A fruit that waits too long and retires must not be granted later."""
    model = FakeModel()
    tracker = TAPNextTracker(
        model=model, match_threshold_px=120, buffer_size=2, rebootstrap_interval=5
    )
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(0, [_det(100, 100)]))
    tracker.update_frame(_frame())
    tracker.update(FrameDetections(1, [_det(600, 300)]))
    assert tracker._pending_queries == [2]
    # Both tracks age; the seed track 1 retires first (frames 1,2,3 empty).
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(2, []))
    assert tracker._pending_queries == [2]
    assert result.lost_track_ids == []
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(3, []))
    assert 1 in result.lost_track_ids
    assert tracker._pending_queries == [2]
    # The deferred fruit now ages out too, and clears its pending slot.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(4, []))
    assert 2 in result.lost_track_ids
    assert tracker._pending_queries == []
    # Frame 5 is interval-eligible, but nothing is waiting: no reboot, and the
    # retired track is not resurrected into the query set.
    tracker.update_frame(_frame())
    result = tracker.update(FrameDetections(5, []))
    assert tracker._query_track_ids == [1]
    assert result.lost_track_ids == []
    assert tracker._pending_queries == []


# --- real TAPNext wrapper (torch-gated) ---------------------------------------

RUN_TORCH = os.environ.get("RUN_TORCH_TESTS") == "1"
requires_torch = pytest.mark.skipif(
    not RUN_TORCH,
    reason="set RUN_TORCH_TESTS=1 to run TAPNext model tests",
)


def _build_tiny_model():
    """A tiny real TAPNext++ model so the test stays cheap."""
    import torch

    from orchardvision_ml.tracking.tapnext import tapnext_torch
    from orchardvision_ml.tracking.tapnext_model import TAPNextModel

    inner = tapnext_torch.TAPNext(
        image_size=(256, 256),
        width=96,
        depth=2,
        num_heads=4,
        lru_width=96,
    )
    return TAPNextModel(inner, torch.device("cpu"))


@requires_torch
def test_real_model_keeps_fixed_query_set_online() -> None:
    model = _build_tiny_model()
    small = np.zeros((256, 512, 3), np.uint8)

    q0 = np.asarray([[100.0, 100.0], [300.0, 200.0]], np.float32)
    positions, visible, state = model.track_frame(small, query_points_xy=q0)
    assert positions.shape == (2, 2)
    assert visible.shape == (2,)
    assert state.step == 1
    assert state.query_points.shape == (1, 2, 3)

    # A second online frame keeps the same rows: the recurrent state cannot
    # grow, and the wrapper only ever steps state from here on.
    positions, _visible, state = model.track_frame(small, state=state)
    assert positions.shape == (2, 2)
    assert state.step == 2
    assert state.query_points.shape == (1, 2, 3)
    positions, _visible, state = model.track_frame(small, state=state)
    assert positions.shape == (2, 2)
    assert state.step == 3
    assert state.query_points.shape == (1, 2, 3)


@requires_torch
def test_from_checkpoint_requires_a_path() -> None:
    from orchardvision_ml.tracking.tapnext_model import TAPNextModel

    with pytest.raises(ValueError, match="path must be provided"):
        TAPNextModel.from_checkpoint()


@requires_torch
def test_tapnext_tracker_runs_real_tiny_model() -> None:
    """Smoke test: the adapter drives the real model without crashing, and the
    query set never grows (the untrained heads make positions/visibility
    arbitrary, so only structural invariants are asserted here)."""
    model = _build_tiny_model()
    tracker = TAPNextTracker(model=model, match_threshold_px=120)
    tracker.update_frame(np.zeros((360, 640, 3), np.uint8))
    result = tracker.update(FrameDetections(0, [_det(100, 100), _det(300, 200)]))
    assert result.total_tracks == 2
    assert tracker._query_track_ids == [1, 2]
    tracker.update_frame(np.zeros((360, 640, 3), np.uint8))
    result = tracker.update(FrameDetections(1, []))
    assert result.total_tracks == 2
    assert tracker._query_track_ids == [1, 2]
    # A far late fruit still never grows the fixed query set.
    tracker.update_frame(np.zeros((360, 640, 3), np.uint8))
    result = tracker.update(FrameDetections(2, [_det(800, 500)]))
    assert tracker._query_track_ids == [1, 2]
    assert len(result.active_tracks) >= 3


@requires_torch
def test_real_model_rebootstrap_grows_query_set() -> None:
    """The real model accepts a re-seed with a grown query set + replay.

    This is the empirical validation that rebootstrap is legal on the actual
    SSM (unlike appending rows to a live state, which crashes); the untrained
    heads make predictions arbitrary, so only structure is asserted.
    """
    model = _build_tiny_model()
    frame = np.zeros((360, 640, 3), np.uint8)
    tracker = TAPNextTracker(model=model, match_threshold_px=120, rebootstrap_interval=2)

    tracker.update_frame(frame)
    result = tracker.update(FrameDetections(0, [_det(100, 100), _det(300, 200)]))
    assert tracker._query_track_ids == [1, 2]
    tracker.update_frame(frame)
    result = tracker.update(FrameDetections(1, []))
    assert result.lost_track_ids == []
    # Frame 2: new fruit defers a query and the interval (origin 0) is due.
    tracker.update_frame(frame)
    result = tracker.update(FrameDetections(2, [_det(800, 500)]))
    assert tracker._pending_queries == []
    assert tracker._query_track_ids == [1, 2, 3]
    # The model kept running after the re-seed and replay.
    tracker.update_frame(frame)
    result = tracker.update(FrameDetections(3, []))
    assert tracker._query_track_ids == [1, 2, 3]
    assert result.lost_track_ids == []
