"""Fruit detection module.

Public interface: :class:`Detector`, :class:`Detection`, :class:`FrameDetections`.
Concrete implementations: :class:`MockDetector` (offline dev/test), and the
future YOLO-compatible adapter in ``adapter.py``.
"""

from .base import Detection, Detector, FrameDetections
from .mock import MockDetector

__all__ = [
    "Detection",
    "Detector",
    "FrameDetections",
    "MockDetector",
]
