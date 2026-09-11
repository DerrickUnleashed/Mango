"""Fruit detection module.

Public interface: :class:`Detector`, :class:`Detection`, :class:`FrameDetections`.
Concrete implementations: :class:`MockDetector` (offline dev/test) and the
YOLO-compatible adapter in ``yolo.py``.
"""

from .base import Detection, Detector, FrameDetections
from .mock import MockDetector
from .nms import iou, nms
from .yolo import YOLODetector

__all__ = [
    "Detection",
    "Detector",
    "FrameDetections",
    "MockDetector",
    "YOLODetector",
    "iou",
    "nms",
]
