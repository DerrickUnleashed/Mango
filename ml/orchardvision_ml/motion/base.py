"""Camera motion estimation for tracking stability.

A motion estimator measures per-frame camera drift and can compensate
detection coordinates so that downstream tracking, embeddings, and identity
memory operate on a stabilized coordinate frame.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.typing import NDArray

BBox = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class CameraMotionEstimate:
    """Per-frame camera motion, measured from frame-wise differences.

    Attributes:
        dx: Horizontal drift in pixels per frame (positive = right).
        dy: Vertical drift in pixels per frame (positive = down).
        scale: Estimated zoom scale factor (1.0 = no zoom).
        confidence: How reliable the estimate is (0..1).
        source: Name of the estimator that produced this estimate.
        frames_analyzed: Number of frames inspected for this estimate.
    """

    dx: float = 0.0
    dy: float = 0.0
    scale: float = 1.0
    confidence: float = 1.0
    source: str = "static"
    frames_analyzed: int = 0

    @property
    def is_static(self) -> bool:
        return abs(self.dx) < 1e-9 and abs(self.dy) < 1e-9


class MotionEstimator(ABC):
    """Interface for estimating and compensating camera motion."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier used in summaries and UI."""

    @abstractmethod
    def estimate(self, frame_index: int, frame: NDArray | None = None) -> CameraMotionEstimate:
        """Estimate per-frame motion at ``frame_index``."""

    @abstractmethod
    def compensate(self, bbox: BBox, frame_index: int) -> BBox:
        """Map a detected bbox from raw to stabilized camera coordinates.

        The inverse cumulative motion up to ``frame_index`` is subtracted so
        that static objects remain static in the stabilized frame.
        """

    @abstractmethod
    def decompensate(self, bbox: BBox, frame_index: int) -> BBox:
        """Map a stabilized bbox back to raw video coordinates.

        The inverse of :meth:`compensate`: adds the cumulative camera motion
        up to ``frame_index`` so stored/drawn boxes line up with the original
        (non-stabilized) video frames.
        """


class StaticMotionEstimator(MotionEstimator):
    """Trivial estimator for a fixed camera: no motion to compensate."""

    @property
    def name(self) -> str:
        return "static"

    def estimate(self, frame_index: int, frame: NDArray | None = None) -> CameraMotionEstimate:
        del frame
        return CameraMotionEstimate(frames_analyzed=frame_index + 1)

    def compensate(self, bbox: BBox, frame_index: int) -> BBox:
        del frame_index
        return bbox

    def decompensate(self, bbox: BBox, frame_index: int) -> BBox:
        del frame_index
        return bbox
