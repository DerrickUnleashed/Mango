"""Fruit detection module.

Public interface: :class:`Detector`, :class:`Detection`, :class:`FrameDetections`.
Concrete implementations: :class:`MockDetector` (offline dev/test) and the
YOLO-compatible adapter in ``yolo_adapter.py``.
"""

from .base import Detection, Detector, FrameDetections
from .mock import MockDetector, MockFruit
from .nms import iou, nms
from .yolo_adapter import YoloDetector

__all__ = [
    "Detection",
    "Detector",
    "FrameDetections",
    "MockDetector",
    "MockFruit",
    "YoloDetector",
    "iou",
    "nms",
]
