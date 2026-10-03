"""TAPNext++ point-enhanced short-term tracker.

Strategy: keep the detector's bounding boxes as the observation source, but
run Google DeepMind's TAPNext++ online point tracker underneath and use its
*point* tracks for detection association across frames. Each track owns a
query point (the fruit centre); the model tracks it frame-by-frame, masking
it while occluded and re-detecting it when it reappears. Detections are
matched to tracks through the predicted point positions rather than IoU +
Kalman, which buys continuity through fast motion and occlusion for roughly
the same pipeline semantics as the box trackers (tracks, track ids, lost
ids, buffering).

Query lifecycle: TAPNext++ keys its recurrent SSM caches by token position,
so the live online loop cannot grow query rows mid-stream — only a
*re-seed* can change the query set. The tracker therefore seeds a fixed set
on its first frame and carries it for the stream, unless ``rebootstrap_interval``
is set: then a ring of recent frames is kept and, once a new fruit is waiting
for a query and ``rebootstrap_interval`` frames have passed, the model is
re-seeded (fresh state) with the old queries plus the deferred ones and the
ring is replayed forward. ``max_query_points`` bounds the total query rows.
While a fruit waits for a rebootstrap, and for every fruit when rebootstrap is
disabled, it is tracked position-only (last known detection point) — the
behaviour of a plain box tracker.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.detection import Detection, FrameDetections

from .base import Track, Tracker, TrackResult

MAX_TRACK_BUFFER_FRAMES = 30
DEFAULT_MATCH_THRESHOLD_PX = 120.0
DEFAULT_MAX_QUERY_POINTS = 256


def _greedy_match_by_distance(
    det_points: NDArray[np.float64],
    cand_points: NDArray[np.float64],
    threshold: float,
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Greedily pair detections to candidates by Euclidean distance.

    Returns ``(matches, unmatched_detection_indices, unmatched_candidate_indices)``
    with candidate winner-take-all in ascending distance order.
    """
    if len(det_points) == 0 or len(cand_points) == 0:
        return (
            [],
            list(range(len(det_points))),
            list(range(len(cand_points))),
        )
    diff = det_points[:, None, :] - cand_points[None, :, :]
    dists = np.sqrt(np.einsum("...i,...i->...", diff, diff))

    matched_det: set[int] = set()
    matched_cand: set[int] = set()
    matches: list[tuple[int, int]] = []
    for idx in np.argsort(dists.ravel()):
        di, ci = divmod(int(idx), dists.shape[1])
        if di in matched_det or ci in matched_cand:
            continue
        if dists[di, ci] > threshold:
            break
        matches.append((di, ci))
        matched_det.add(di)
        matched_cand.add(ci)

    unmatched_det = [i for i in range(len(det_points)) if i not in matched_det]
    unmatched_cand = [i for i in range(len(cand_points)) if i not in matched_cand]
    return matches, unmatched_det, unmatched_cand


class TAPNextTracker(Tracker):
    """Point-enhanced multi-object tracker backed by TAPNext++.

    Args:
        checkpoint_path: Path to the downloaded TAPNext++ checkpoint. Ignored
            when ``model`` is injected; required otherwise.
        device: Torch device; ``None`` auto-selects CUDA then CPU.
        input_resolution: Square model resolution (``256`` or ``512``); it
            must match the checkpoint.
        model: Pre-built model exposing ``track_frame(frame_bgr,
            query_points_xy=None, state=None) -> (positions_xy, visible,
            state)``. Used by tests and callers that manage model loading.
        match_threshold_px: Detections farther than this (display pixels)
            from every track's last point count as new tracks.
        buffer_size: Frames a track survives without a matched detection
            before it is reported lost.
        max_query_points: Upper bound on model query rows, including rows
            granted by rebootstrap (the model's point capacity). Fruits beyond
            the bound are tracked position-only.
        rebootstrap_interval: Frames between model re-seeds that grant deferred
            queries to fruits first seen mid-stream. ``0`` (the default)
            disables rebootstrap and falls back to position-only tracking for
            all post-seed fruits; larger values trade replay cost (a forward
            pass per buffered frame) for fresher queries. Reboots only happen
            when a fruit is actually waiting for a query.
    """

    supports_frame_input = True

    def __init__(
        self,
        checkpoint_path: str | Path | None = None,
        *,
        device: str | None = None,
        input_resolution: int = 256,
        model: Any | None = None,
        match_threshold_px: float = DEFAULT_MATCH_THRESHOLD_PX,
        buffer_size: int = MAX_TRACK_BUFFER_FRAMES,
        max_query_points: int = DEFAULT_MAX_QUERY_POINTS,
        rebootstrap_interval: int = 0,
    ) -> None:
        self.checkpoint_path = checkpoint_path
        self.device = device
        self.input_resolution = input_resolution
        self.match_threshold_px = match_threshold_px
        self.buffer_size = buffer_size
        self.max_query_points = max_query_points
        self.rebootstrap_interval = rebootstrap_interval

        self._model: Any | None = model
        self._state: Any | None = None
        self._frame: NDArray[np.uint8] | None = None
        self._query_track_ids: list[int] = []
        self._pending_queries: list[int] = []
        self._frame_buffer: deque[NDArray[np.uint8]] = deque()
        self._bootstrap_frame_id: int | None = None
        self._tracks: dict[int, Track] = {}
        self._frames_since_match: dict[int, int] = {}
        self._last_points: dict[int, tuple[float, float]] = {}
        self._last_visible: dict[int, bool] = {}
        self._next_track_id = 1

    @property
    def name(self) -> str:
        return "tapnext++"

    def update_frame(self, frame: NDArray[np.uint8]) -> None:
        """Cache the current frame for the model call in :meth:`update`."""
        self._frame = frame

    def update(self, detections: FrameDetections) -> TrackResult:
        frame = self._require_frame()
        model = self._ensure_model()
        frame_id = detections.frame_id
        dets = detections.detections

        if self.rebootstrap_interval > 0:
            self._frame_buffer.append(frame)
            if len(self._frame_buffer) > self.rebootstrap_interval + 1:
                self._frame_buffer.popleft()

        # Detections that do not sit near any existing track become new
        # tracks. On the first frame they claim a query row directly (the
        # seeded set is fixed for that seed); on later frames they are
        # deferred to a rebootstrap (when enabled, else position-only) but
        # still get a detection on their first frame.
        pending_new = self._find_new_detections(dets)
        pending_set = {idx for idx, _ in pending_new}
        new_track_ids: list[int] = []
        fresh_tids: set[int] = set()

        seed_xy: list[list[float]] = []
        seed_tids: list[int] = []
        seed_capacity = self.max_query_points if self._state is None else 0
        for position, (_idx, det) in enumerate(pending_new):
            tid = self._allocate_track_id()
            trk = Track(track_id=tid)
            self._tracks[tid] = trk
            self._frames_since_match[tid] = 0
            trk.update(frame_id, det)
            self._last_points[tid] = (det.center[0], det.center[1])
            self._last_visible[tid] = True
            new_track_ids.append(tid)
            fresh_tids.add(tid)
            if position < seed_capacity:
                seed_xy.append([det.center[0], det.center[1]])
                seed_tids.append(tid)
            elif self._can_defer_query():
                self._pending_queries.append(tid)

        # A rebootstrap replaces this frame's step: the replay ends with the
        # model already advanced through the current frame.
        if not self._maybe_rebootstrap(model, frame_id):
            self._advance_model(model, frame, seed_xy, seed_tids)

        if self._state is not None and self._bootstrap_frame_id is None:
            self._bootstrap_frame_id = frame_id
            if self.rebootstrap_interval > 0:
                self._frame_buffer.clear()
                self._frame_buffer.append(frame)

        remaining = [idx for idx in range(len(dets)) if idx not in pending_set]
        new_track_ids.extend(self._associate(frame_id, dets, remaining, fresh_tids))

        return self._retire_and_report(frame_id, new_track_ids)

    def _advance_model(
        self,
        model: Any,
        frame: NDArray[np.uint8],
        seed_xy: list[list[float]],
        seed_tids: list[int],
    ) -> None:
        """Step the online model once; seed its fixed query set on first use."""
        if self._state is None:
            if not seed_xy:
                return
            seed_arr = np.asarray(seed_xy, dtype=np.float32)
            positions, visible, self._state = model.track_frame(frame, query_points_xy=seed_arr)
            self._query_track_ids = list(seed_tids)
        else:
            positions, visible, self._state = model.track_frame(frame, state=self._state)

        for i, tid in enumerate(self._query_track_ids):
            self._last_points[tid] = (float(positions[i][0]), float(positions[i][1]))
            self._last_visible[tid] = bool(visible[i])

    def _can_defer_query(self) -> bool:
        """Whether a new mid-stream fruit may wait for a rebootstrap query."""
        return (
            self._state is not None
            and self.rebootstrap_interval > 0
            and len(self._query_track_ids) + len(self._pending_queries) < self.max_query_points
        )

    def _maybe_rebootstrap(self, model: Any, frame_id: int) -> bool:
        """Re-seed the model with deferred queries and replay the frame ring.

        The live SSM caches cannot grow query rows, so granting a late fruit a
        query requires restarting the model from the last bootstrapped frame
        with the full query set (old queries re-seed at their predicted
        position, deferred queries join now) and replaying the buffered frames
        through to the current one. Returns ``True`` when a rebootstrap ran
        (and the surrounding step should therefore be skipped).
        """
        if self.rebootstrap_interval <= 0:
            return False
        if not self._pending_queries:
            return False
        if self._bootstrap_frame_id is None:
            return False
        if frame_id - self._bootstrap_frame_id < self.rebootstrap_interval:
            return False
        if not self._frame_buffer:
            return False

        pending_tids = list(self._pending_queries)
        query_xy = [self._last_points[tid] for tid in self._query_track_ids]
        query_xy += [self._last_points[tid] for tid in pending_tids]

        frames = list(self._frame_buffer)
        positions, visible, state = model.track_frame(
            frames[0], query_points_xy=np.asarray(query_xy, dtype=np.float32)
        )
        for frm in frames[1:]:
            positions, visible, state = model.track_frame(frm, state=state)

        self._state = state
        self._query_track_ids = self._query_track_ids + pending_tids
        for i, tid in enumerate(self._query_track_ids):
            self._last_points[tid] = (float(positions[i][0]), float(positions[i][1]))
            self._last_visible[tid] = bool(visible[i])

        self._pending_queries.clear()
        self._frame_buffer.clear()
        self._bootstrap_frame_id = frame_id
        return True

    def _associate(
        self,
        frame_id: int,
        dets: list[Detection],
        det_indices: list[int],
        fresh_tids: set[int],
    ) -> list[int]:
        """Match remaining detections to visible candidates; buffer leftovers.

        Candidates are query tracks whose point is currently visible plus
        position-only tracks (their last known point acts as a stand-in for a
        model query). Returns track ids created for detections that matched
        nothing.
        """
        cand_points: list[list[float]] = []
        cand_tids: list[int] = []
        query_set = set(self._query_track_ids)
        for tid in self._tracks:
            if tid in query_set and not self._last_visible.get(tid, False):
                continue
            point = self._last_points.get(tid)
            if point is None:
                continue
            cand_points.append([point[0], point[1]])
            cand_tids.append(tid)

        det_points = np.asarray([dets[i].center for i in det_indices], dtype=np.float64)
        cand_arr = np.asarray(cand_points, dtype=np.float64)
        matches, _, _ = _greedy_match_by_distance(det_points, cand_arr, self.match_threshold_px)

        matched_tids: set[int] = set()
        matched_dets: set[int] = set()
        for di, ci in matches:
            det = dets[det_indices[di]]
            tid = cand_tids[ci]
            self._tracks[tid].update(frame_id, det)
            self._frames_since_match[tid] = 0
            matched_tids.add(tid)
            matched_dets.add(det_indices[di])

        new_track_ids: list[int] = []
        fresh_tids.update(new_track_ids)
        for idx in det_indices:
            if idx in matched_dets:
                continue
            det = dets[idx]
            tid = self._allocate_track_id()
            self._tracks[tid] = Track(track_id=tid)
            self._tracks[tid].update(frame_id, det)
            self._frames_since_match[tid] = 0
            self._last_points[tid] = (det.center[0], det.center[1])
            self._last_visible[tid] = True
            new_track_ids.append(tid)

        for tid in self._tracks:
            if tid not in matched_tids and tid not in fresh_tids:
                self._frames_since_match[tid] = self._frames_since_match.get(tid, 0) + 1

        return new_track_ids

    def _retire_and_report(self, frame_id: int, new_track_ids: list[int]) -> TrackResult:
        lost_track_ids: list[int] = []
        for tid in list(self._tracks):
            if self._frames_since_match.get(tid, 0) > self.buffer_size:
                lost_track_ids.append(tid)
                self._tracks.pop(tid)
                self._frames_since_match.pop(tid, None)
                self._last_points.pop(tid, None)
                self._last_visible.pop(tid, None)
                if tid in self._pending_queries:
                    self._pending_queries.remove(tid)

        return TrackResult(
            frame_id=frame_id,
            active_tracks=list(self._tracks.values()),
            new_track_ids=new_track_ids,
            lost_track_ids=lost_track_ids,
            total_tracks=len(self._tracks),
        )

    def _find_new_detections(self, dets: list[Detection]) -> list[tuple[int, Detection]]:
        """Detections that do not sit near any existing track's last point."""
        result: list[tuple[int, Detection]] = []
        for idx, det in enumerate(dets):
            cx, cy = det.center
            if self._near_existing(cx, cy):
                continue
            result.append((idx, det))
        return result

    def _near_existing(self, x: float, y: float) -> bool:
        threshold_sq = self.match_threshold_px**2
        return any(
            (x - px) ** 2 + (y - py) ** 2 <= threshold_sq for px, py in self._last_points.values()
        )

    def _allocate_track_id(self) -> int:
        tid = self._next_track_id
        self._next_track_id += 1
        return tid

    def _require_frame(self) -> NDArray[np.uint8]:
        if self._frame is None:
            raise RuntimeError(
                "update_frame() must be called before update(); the pipeline "
                "does this automatically when tracker.supports_frame_input."
            )
        return self._frame

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        if self.checkpoint_path is None:
            raise ValueError(
                "TAPNextTracker needs checkpoint_path (or an injected model). "
                "Download weights with scripts/download_tapnext_weights.py."
            )
        import torch

        from .tapnext_model import TAPNextModel

        device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model = TAPNextModel.from_checkpoint(
            str(self.checkpoint_path),
            device=device,
            input_resolution=self.input_resolution,
        )
        return self._model
