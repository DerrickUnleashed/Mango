"""Detector abstraction for fruit detection.

The ``Detector`` interface intentionally avoids coupling to a specific model.
A YOLO-compatible adapter, a legacy detector, or the deterministic mock can all
implement it. Detection output uses plain dataclasses so the interface is
trivially testable without a GPU.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class Detection:
    """A single detected object in a frame.

    Attributes:
        bbox: ``[x, y, width, height]`` in pixel coordinates.
        confidence: Detection confidence in ``[0, 1]``.
        class_label: Class name (defaults to ``"mango"``).
        track_id: Optional short-term track assignment (filled by the tracker).
    """

    bbox: tuple[float, float, float, float]
    confidence: float
    class_label: str = "mango"
    track_id: int | None = None

    @property
    def center(self) -> tuple[float, float]:
        x, y, w, h = self.bbox
        return (x + w / 2.0, y + h / 2.0)


@dataclass(slots=True)
class FrameDetections:
    """Detections produced for a single frame."""

    frame_id: int
    detections: list[Detection] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.detections)

    def __bool__(self) -> bool:
        return bool(self.detections)


class Detector(ABC):
    """Abstract fruit detector."""

    @abstractmethod
    def detect(self, frame: NDArray[np.uint8], frame_id: int) -> FrameDetections:
        """Run detection on a single BGR image frame.

        Args:
            frame: Image as an ``(H, W, 3)`` uint8 BGR array.
            frame_id: Zero-based frame index.

        Returns:
            Detections with bounding boxes, confidence, and class labels.
        """

    @property
    def name(self) -> str:
        """Human-readable detector identifier (for experiment provenance)."""
        return self.__class__.__name__


class FrameScaler:
    """Utility to keep detection coordinates consistent after frame resizing."""

    def __init__(
        self,
        orig_w: int,
        orig_h: int,
        target_w: int | None = None,
        target_h: int | None = None,
    ) -> None:
        self.orig_w = orig_w
        self.orig_h = orig_h
        self.target_w = target_w or orig_w
        self.target_h = target_h or orig_h
        self.sx = self.target_w / orig_w if orig_w else 1.0
        self.sy = self.target_h / orig_h if orig_h else 1.0

    def to_original(
        self, x: float, y: float, w: float, h: float
    ) -> tuple[float, float, float, float]:
        return (x / self.sx, y / self.sy, w / self.sx, h / self.sy)
