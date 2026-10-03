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

Query lifecycle: unmatched detections start a new track and seed a query
point on the current frame. Query rows are append-only for the life of the
run — the recurrent model assigns state per token position, so a row cannot
be popped without invalidating the SSM caches. ``max_query_points`` bounds
stream length; once the cap is reached, new fruits are still tracked through
their last known position (no model query) until the stream ends. Reclaiming
query slots by periodically re-seeding the model (a TAPNext "rebootstrap")
is future work.
"""

from __future__ import annotations

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
        max_query_points: Upper bound on live model query rows. Once reached,
            new fruits fall back to position-only association.
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
    ) -> None:
        self.checkpoint_path = checkpoint_path
        self.device = device
        self.input_resolution = input_resolution
        self.match_threshold_px = match_threshold_px
        self.buffer_size = buffer_size
        self.max_query_points = max_query_points

        self._model: Any | None = model
        self._state: Any | None = None
        self._frame: NDArray[np.uint8] | None = None
        self._query_track_ids: list[int] = []
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

        # Detections that do not sit near any existing track become new
        # tracks. Seedable ones (within the query cap) also get a model query
        # point at their centre; the rest are position-only tracks.
        pending_new = self._find_new_detections(dets)
        pending_set = {idx for idx, _ in pending_new}
        new_track_ids: list[int] = []

        seed_xy: list[list[float]] = []
        seed_tids: list[int] = []
        seed_capacity = max(0, self.max_query_points - len(self._query_track_ids))
        for position, (_idx, det) in enumerate(pending_new):
            tid = self._allocate_track_id()
            trk = Track(track_id=tid)
            self._tracks[tid] = trk
            self._frames_since_match[tid] = 0
            trk.update(frame_id, det)
            self._last_points[tid] = (det.center[0], det.center[1])
            self._last_visible[tid] = True
            new_track_ids.append(tid)
            if position < seed_capacity:
                seed_xy.append([det.center[0], det.center[1]])
                seed_tids.append(tid)

        self._advance_model(
            model,
            frame,
            np.asarray(seed_xy, dtype=np.float32) if seed_xy else None,
            seed_tids,
        )

        remaining = [idx for idx in range(len(dets)) if idx not in pending_set]
        new_track_ids.extend(self._associate(frame_id, dets, remaining))

        return self._retire_and_report(frame_id, new_track_ids)

    def _advance_model(
        self,
        model: Any,
        frame: NDArray[np.uint8],
        seed_xy: NDArray[np.float32] | None,
        seed_tids: list[int],
    ) -> None:
        """Step the online model once, seeding new query rows when needed."""
        if self._state is None:
            if seed_xy is None:
                return
            positions, visible, self._state = model.track_frame(frame, query_points_xy=seed_xy)
            self._query_track_ids = list(seed_tids)
        elif seed_xy is not None:
            positions, visible, self._state = model.track_frame(
                frame, query_points_xy=seed_xy, state=self._state
            )
            self._query_track_ids = list(self._query_track_ids) + list(seed_tids)
        else:
            positions, visible, self._state = model.track_frame(frame, state=self._state)

        for i, tid in enumerate(self._query_track_ids):
            self._last_points[tid] = (float(positions[i][0]), float(positions[i][1]))
            self._last_visible[tid] = bool(visible[i])

    def _associate(
        self,
        frame_id: int,
        dets: list[Detection],
        det_indices: list[int],
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
            if tid not in matched_tids:
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
