"""Mock camera motion estimator with deterministic constant drift.

Replaces frame-difference estimation while real adapters are under
development. The per-frame drift is constant, so the cumulative offset at a
given frame is simply ``drift * frame_index``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BBox, CameraMotionEstimate, MotionEstimator

if TYPE_CHECKING:
    from numpy.typing import NDArray


class MockMotionEstimator(MotionEstimator):
    """Estimator that reports a constant per-frame camera drift."""

    def __init__(
        self,
        dx_per_frame: float = 0.5,
        dy_per_frame: float = 0.0,
        name: str = "mock-drift",
    ) -> None:
        self._dx = dx_per_frame
        self._dy = dy_per_frame
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def estimate(self, frame_index: int, frame: NDArray | None = None) -> CameraMotionEstimate:
        del frame
        return CameraMotionEstimate(
            dx=self._dx,
            dy=self._dy,
            scale=1.0,
            confidence=0.95,
            source=self._name,
            frames_analyzed=frame_index + 1,
        )

    def compensate(self, bbox: BBox, frame_index: int) -> BBox:
        x, y, w, h = bbox
        return (
            max(0.0, x - self._dx * frame_index),
            max(0.0, y - self._dy * frame_index),
            w,
            h,
        )
