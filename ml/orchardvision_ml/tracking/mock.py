"""Deterministic mock tracker for development and testing."""

from __future__ import annotations

from dataclasses import dataclass, field

from orchardvision_ml.detection import FrameDetections

from .base import (
    Track,
    Tracker,
    TrackResult,
    associate_by_center_distance,
)

MAX_MATCH_DISTANCE_PX = 120.0
MAX_TRACK_BUFFER_FRAMES = 30


@dataclass(slots=True)
class MockTracker(Tracker):
    """Simple short-term tracker based on centre-distance association.

    Deterministic, dependency-free, and adequate for development: tracks are
    matched greedily by centre distance; unmatched detections start new tracks;
    unmatched tracks are kept in a short buffer (to survive brief missed
    detections caused by the mock detector's occlusion windows) and then
    removed. Track IDs are monotonically increasing and never reused within a
    stream, which keeps identity bookkeeping unambiguous downstream.
    """

    match_threshold: float = MAX_MATCH_DISTANCE_PX
    max_buffer: int = MAX_TRACK_BUFFER_FRAMES

    _tracks: dict[int, Track] = field(default_factory=dict)
    _frames_since_match: dict[int, int] = field(default_factory=dict)
    _next_track_id: int = field(default=1)

    @property
    def name(self) -> str:
        return "mock-tracker"

    def update(self, detections: FrameDetections) -> TrackResult:
        frame_id = detections.frame_id
        active = list(self._tracks.values())

        matches, unmatched_det, unmatched_trk = associate_by_center_distance(
            detections.detections, active, threshold=self.match_threshold
        )

        new_track_ids: list[int] = []
        lost_track_ids: list[int] = []

        for det_idx, trk_idx in matches:
            track = active[trk_idx]
            track.update(frame_id, detections.detections[det_idx])
            self._frames_since_match[track.track_id] = 0

        for det_idx in unmatched_det:
            det = detections.detections[det_idx]
            tid = self._next_id()
            track = Track(track_id=tid)
            track.update(frame_id, det)
            self._tracks[tid] = track
            self._frames_since_match[tid] = 0
            new_track_ids.append(tid)

        for trk_idx in unmatched_trk:
            track = active[trk_idx]
            self._frames_since_match[track.track_id] = (
                self._frames_since_match.get(track.track_id, 0) + 1
            )
            if self._frames_since_match[track.track_id] >= self.max_buffer:
                lost_track_ids.append(track.track_id)

        for tid in list(self._tracks):
            if tid in lost_track_ids:
                self._tracks.pop(tid)
                self._frames_since_match.pop(tid, None)

        return TrackResult(
            frame_id=frame_id,
            active_tracks=list(self._tracks.values()),
            new_track_ids=new_track_ids,
            lost_track_ids=lost_track_ids,
            total_tracks=len(self._tracks),
        )

    def _next_id(self) -> int:
        tid = self._next_track_id
        self._next_track_id += 1
        return tid
