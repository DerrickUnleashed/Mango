"""End-to-end pipeline evaluation against mock scenario ground truth."""

from __future__ import annotations

import numpy as np

from orchardvision_ml.detection import MockDetector
from orchardvision_ml.tracking import ByteTrackAdapter, MockTracker, Tracker
from orchardvision_ml.tracking.base import TrackResult

from .metrics import MetricsReport, evaluate
from .scenario import ground_truth_trajectories
from .tracks import Tracklet


def _dummy_frame() -> np.ndarray:
    """1280x720 dark canvas; mock detection ignores pixels."""
    return np.zeros((720, 1280, 3), dtype=np.uint8)


def _build_tracker(name: str) -> Tracker:
    if name == "bytetrack":
        return ByteTrackAdapter()
    return MockTracker()


def build_predicted_tracks(result: TrackResult | None) -> list[Tracklet]:
    """Build predicted tracklets from a tracker's final active tracks."""
    if result is None:
        return []
    tracks: list[Tracklet] = []
    for track in result.active_tracks:
        tracks.append(
            Tracklet(
                object_id=track.track_id,
                observations=tuple(
                    (
                        p.frame_id,
                        (float(p.bbox[0]), float(p.bbox[1]), float(p.bbox[2]), float(p.bbox[3])),
                    )
                    for p in track.points
                ),
            )
        )
    return tracks


def evaluate_scenario(
    scenario: list,
    num_frames: int,
    tracker: str = "mock",
    recovered: int = 0,
    total_gaps: int = 0,
) -> tuple[MetricsReport, list[Tracklet], list[Tracklet]]:
    """Run the mock detector + chosen tracker and score against official trajectories."""
    detector = MockDetector(scenario=scenario)
    track = _build_tracker(tracker)
    frame = _dummy_frame()

    result = None
    for index in range(num_frames):
        detection = detector.detect(frame, index)
        result = track.update(detection)

    gt = ground_truth_trajectories(scenario, num_frames)
    pred = build_predicted_tracks(result)
    report = evaluate(gt, pred, recovered=recovered, total_gaps=total_gaps)
    return report, gt, pred
