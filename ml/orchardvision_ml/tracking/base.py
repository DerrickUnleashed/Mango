"""Tracker abstraction for short-term multi-object tracking.

Tracks associate detections across consecutive frames. Each track gets a
persistent integer ``track_id`` and accumulates a list of ``TrackPoint``
observations with bounding boxes, confidence, and timestamps.

The tracker interface is deliberately minimal — any tracking algorithm
(ByteTrack, SORT, DeepSORT, a trivial IoU matcher) can implement it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from orchardvision_ml.detection import Detection, FrameDetections


@dataclass(slots=True)
class TrackPoint:
    """A single observation for a track."""

    frame_id: int
    bbox: tuple[float, float, float, float]
    confidence: float
    is_occluded: bool = False


@dataclass(slots=True)
class Track:
    """A complete or in-progress track across consecutive frames."""

    track_id: int
    points: list[TrackPoint] = field(default_factory=list)
    last_frame_id: int = -1

    def update(self, frame_id: int, det: Detection, is_occluded: bool = False) -> None:
        self.points.append(
            TrackPoint(
                frame_id=frame_id,
                bbox=det.bbox,
                confidence=det.confidence,
                is_occluded=is_occluded,
            )
        )
        self.last_frame_id = frame_id

    @property
    def length(self) -> int:
        return len(self.points)

    @property
    def current_bbox(self) -> tuple[float, float, float, float] | None:
        return self.points[-1].bbox if self.points else None

    @property
    def average_confidence(self) -> float:
        return sum(p.confidence for p in self.points) / len(self.points) if self.points else 0.0


@dataclass(slots=True)
class TrackResult:
    """Output of a single tracker update step."""

    frame_id: int
    active_tracks: list[Track]
    new_track_ids: list[int]
    lost_track_ids: list[int]
    total_tracks: int


def _next_track_id(used: set[int]) -> int:
    i = 1
    while i in used:
        i += 1
    return i


class Tracker(ABC):
    """Abstract short-term tracker."""

    @abstractmethod
    def update(self, detections: FrameDetections) -> TrackResult:
        """Process detections for the current frame and return updated tracks."""

    @property
    def name(self) -> str:
        return self.__class__.__name__


def associate_by_center_distance(
    detections: list[Detection],
    active_tracks: list[Track],
    threshold: float = 80.0,
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Associate detections to tracks by centre-point Euclidean distance.

    Returns (matches, unmatched_detection_indices, unmatched_track_indices).
    """
    if not active_tracks or not detections:
        return ([], list(range(len(detections))), list(range(len(active_tracks))))

    det_centres = np.array([d.center for d in detections])
    trk_centres = np.array([t.current_bbox for t in active_tracks])
    if trk_centres.size == 0:
        return ([], list(range(len(detections))), list(range(len(active_tracks))))

    trk_xy = trk_centres[:, :2] + trk_centres[:, 2:] / 2.0
    diff = det_centres[:, None, :] - trk_xy[None, :, :]
    dists = np.linalg.norm(diff, axis=2)

    matched_det = set()
    matched_trk = set()
    matches: list[tuple[int, int]] = []

    order = np.argsort(dists.ravel())
    for idx in order:
        di, ti = divmod(int(idx), len(active_tracks))
        if di in matched_det or ti in matched_trk:
            continue
        if dists[di, ti] > threshold:
            break
        matches.append((di, ti))
        matched_det.add(di)
        matched_trk.add(ti)

    unmatched_det = [i for i in range(len(detections)) if i not in matched_det]
    unmatched_trk = [i for i in range(len(active_tracks)) if i not in matched_trk]

    return matches, unmatched_det, unmatched_trk
