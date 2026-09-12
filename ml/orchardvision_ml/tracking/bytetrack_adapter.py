"""ByteTrack-compatible tracker adapter.

Implements ByteTrack's core strategy using this package's Kalman filter and a
two-stage data association:

1. High-confidence detections (>= ``high_threshold``) are matched to Kalman
   predictions first using IoU.
2. Remaining high- and low-confidence detections are matched in a second pass
   (ByteTrack's low-confidence association), allowing pairs that survived
   detection-score dips to reconnect to buffered lost tracks.

A pure intersection-over-union fallback is used here; the adapter can be
swapped for the reference ByteTrack/JDE implementation in model mode without
changing the :class:`Tracker` interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from orchardvision_ml.detection import Detection, FrameDetections

from .base import Track, Tracker, TrackResult
from .kalman import KalmanBoxFilter, to_tlwh, to_xyah

MAX_TRACK_BUFFER_FRAMES = 30


@dataclass(slots=True)
class _TrackState:
    track_id: int
    filter: KalmanBoxFilter
    frames_since_update: int = 0
    initialized: bool = False
    track: Track = field(init=False)

    def __post_init__(self) -> None:
        self.track = Track(track_id=self.track_id)


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _iou_matrix(
    boxes_a: list[tuple[float, float, float, float]],
    boxes_b: list[tuple[float, float, float, float]],
) -> np.ndarray:
    if not boxes_a or not boxes_b:
        return np.zeros((len(boxes_a), len(boxes_b)))
    return np.array([[_iou(a, b) for b in boxes_b] for a in boxes_a], dtype=np.float64)


def _greedy_matches(
    iou_matrix: np.ndarray, min_iou: float
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    matched_a: set[int] = set()
    matched_b: set[int] = set()
    matches: list[tuple[int, int]] = []
    order = np.argsort(iou_matrix.ravel())[::-1]
    for idx in order:
        ai, bi = divmod(int(idx), iou_matrix.shape[1])
        if ai in matched_a or bi in matched_b:
            continue
        if iou_matrix[ai, bi] < min_iou:
            break
        matches.append((ai, bi))
        matched_a.add(ai)
        matched_b.add(bi)
    unmatched_a = [i for i in range(iou_matrix.shape[0]) if i not in matched_a]
    unmatched_b = [i for i in range(iou_matrix.shape[1]) if i not in matched_b]
    return matches, unmatched_a, unmatched_b


class ByteTrackAdapter(Tracker):
    """ByteTrack-style tracker operating on a per-frame detection stream."""

    def __init__(
        self,
        high_threshold: float = 0.5,
        match_iou: float = 0.2,
        buffer_size: int = MAX_TRACK_BUFFER_FRAMES,
    ) -> None:
        self.high_threshold = high_threshold
        self.match_iou = match_iou
        self.buffer_size = buffer_size
        self._tracks: dict[int, _TrackState] = {}
        self._next_id = 1

    @property
    def name(self) -> str:
        return "bytetrack-adapter"

    def update(self, detections: FrameDetections) -> TrackResult:
        frame_id = detections.frame_id
        dets = detections.detections

        track_states = list(self._tracks.values())

        # Kalman predict step for all alive tracks
        for st in track_states:
            st.filter.predict()
            st.frames_since_update += 1

        high_dets = [d for d in dets if d.confidence >= self.high_threshold]
        low_dets = [d for d in dets if d.confidence < self.high_threshold]
        high_global: list[int] = []
        low_global: list[int] = []
        for gi, d in enumerate(dets):
            if d.confidence >= self.high_threshold:
                high_global.append(gi)
            else:
                low_global.append(gi)

        matched_det_global: set[int] = set()
        matched_track: set[int] = set()

        # Stage 1: match high-confidence detections to Kalman predictions
        predicted = [to_tlwh(st.filter.get_estimate_xyah()) for st in track_states]
        high_boxes = [d.bbox for d in high_dets]
        matches, unmatched_high, _ = _greedy_matches(
            _iou_matrix(high_boxes, predicted), self.match_iou
        )

        for det_idx, trk_idx in matches:
            st = track_states[trk_idx]
            self._apply(st, frame_id, high_dets[det_idx])
            matched_det_global.add(high_global[det_idx])
            matched_track.add(trk_idx)

        # Stage 2: form a candidate pool from everything not yet matched in stage 1
        # (unmatched high detections + all low-confidence detections) and match it
        # against the remaining (lost/buffered) tracks.
        remaining_track_idx = [i for i in range(len(track_states)) if i not in matched_track]
        unmatched_high_dets = [high_dets[i] for i in unmatched_high]
        second_pool = unmatched_high_dets + low_dets
        second_boxes = [d.bbox for d in second_pool]
        track_boxes = []
        for i in remaining_track_idx:
            st = track_states[i]
            last_bbox = st.track.current_bbox
            if st.frames_since_update > 0 and last_bbox is not None:
                track_boxes.append(last_bbox)
            else:
                track_boxes.append(to_tlwh(st.filter.get_estimate_xyah()))
        matches2, _, _ = _greedy_matches(_iou_matrix(second_boxes, track_boxes), self.match_iou)

        for det_idx, trk_idx in matches2:
            st = track_states[remaining_track_idx[trk_idx]]
            self._apply(st, frame_id, second_pool[det_idx])
            if det_idx < len(unmatched_high_dets):
                det_global = high_global[unmatched_high[det_idx]]
            else:
                det_global = low_global[det_idx - len(unmatched_high_dets)]
            matched_det_global.add(det_global)
            matched_track.add(remaining_track_idx[trk_idx])

        # New tracks only for high-confidence detections that stayed unmatched
        # through both association stages (ByteTrack: low detections never start tracks)
        new_track_ids: list[int] = []
        for det_idx in unmatched_high:
            global_idx = high_global[det_idx]
            if global_idx in matched_det_global:
                continue
            det = high_dets[det_idx]
            st = self._init_track(det)
            self._apply(st, frame_id, det)
            new_track_ids.append(st.track_id)

        # Retire stale tracks past the buffer window
        lost_track_ids = [
            st.track_id for st in track_states if st.frames_since_update > self.buffer_size
        ]
        for tid in lost_track_ids:
            self._tracks.pop(tid)

        return TrackResult(
            frame_id=frame_id,
            active_tracks=[st.track for st in self._tracks.values()],
            new_track_ids=new_track_ids,
            lost_track_ids=lost_track_ids,
            total_tracks=len(self._tracks),
        )

    def _init_track(self, det: Detection) -> _TrackState:
        st = _TrackState(track_id=self._next_id, filter=KalmanBoxFilter())
        self._next_id += 1
        self._tracks[st.track_id] = st
        return st

    def _apply(self, st: _TrackState, frame_id: int, det: Detection) -> None:
        if not st.initialized:
            st.filter.initiate(to_xyah(det.bbox))
            st.initialized = True
        else:
            st.filter.update(to_xyah(det.bbox))
        st.frames_since_update = 0
        st.track.update(frame_id, det)
