"""Camera-motion estimator measured from the detections themselves.

The estimators shipped in ``orchardvision_ml.motion`` are synthetic: ``static`` assumes a fixed
camera and ``MockMotionEstimator`` simulates drift. Neither can say whether compensating a real
handheld clip helps, which is what the evaluation in Chapter 8 needs to answer.

This estimator measures the real global shift of a frame from the box centres, which is the same
signal a phase-correlation implementation would use, and it implements the
:class:`~orchardvision_ml.motion.base.MotionEstimator` interface so the pipeline can use it
unchanged: boxes are compensated into stabilized coordinates before tracking and decompensated
before they are stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.motion.base import BBox, CameraMotionEstimate, MotionEstimator


def centre(bbox: BBox) -> NDArray[np.float64]:
    x, y, w, h = bbox
    return np.array([x + w / 2, y + h / 2])


@dataclass
class MeasuredMotionEstimator(MotionEstimator):
    """Global shift accumulated from the median displacement of detections.

    Per-frame steps are supplied by the caller as the video is processed, because the estimate
    depends on the detections of the previous frame and cannot be known ahead of time.
    """

    min_boxes: int = 3
    steps: dict[int, tuple[float, float]] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return "measured"

    def observe(self, frame_index: int, previous: list[BBox], current: list[BBox]) -> None:
        """Record the shift between two consecutive frames from their box centres."""
        if len(previous) < self.min_boxes or len(current) < self.min_boxes:
            return
        before = np.stack([centre(b) for b in previous])
        after = np.stack([centre(b) for b in current])
        # Consecutive frames can hold different numbers of detections, so pair the
        # two sets by position order and take the median of the surviving pairs.
        common = min(len(before), len(after))
        if common < self.min_boxes:
            return
        step = np.median(after[:common] - before[:common], axis=0)
        self.steps[frame_index] = (float(step[0]), float(step[1]))

    def cumulative(self, frame_index: int) -> tuple[float, float]:
        dx = dy = 0.0
        for index in range(frame_index + 1):
            step = self.steps.get(index)
            if step is not None:
                dx += step[0]
                dy += step[1]
        return dx, dy

    def estimate(self, frame_index: int, frame: NDArray | None = None) -> CameraMotionEstimate:
        del frame
        dx, dy = self.cumulative(frame_index)
        return CameraMotionEstimate(dx=dx, dy=dy, frames_analyzed=frame_index + 1)

    def compensate(self, bbox: BBox, frame_index: int) -> BBox:
        """Shift a raw box back by the cumulative shift seen so far."""
        dx, dy = self.cumulative(frame_index)
        x, y, w, h = bbox
        return (x - dx, y - dy, w, h)

    def decompensate(self, bbox: BBox, frame_index: int) -> BBox:
        """Shift a stabilized box forward again, for storage and drawing."""
        dx, dy = self.cumulative(frame_index)
        x, y, w, h = bbox
        return (x + dx, y + dy, w, h)
