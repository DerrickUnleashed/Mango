"""Tests for the YOLOv8 detector adapter.

These tests require ``ultralytics`` to be installed.  The integration test
(``test_yolo_detect_on_real_image``) also needs a pretrained ``yolov8n.pt``
checkpoint — it is downloaded automatically on first run by ultralytics.
"""

from __future__ import annotations

import pathlib

import cv2
import numpy as np
import pytest

from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.detection.yolo_adapter import YoloDetector

try:
    from ultralytics import YOLO  # noqa: F401

    HAS_ULTRALYTICS = True
except ImportError:
    HAS_ULTRALYTICS = False

DATA_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "Mango_Dataset2"
SAMPLE_IMAGE = DATA_DIR / "test" / "images"

pytestmark = pytest.mark.skipif(not HAS_ULTRALYTICS, reason="ultralytics not installed")


@pytest.fixture(scope="module")
def yolo_detector() -> YoloDetector:
    """Load a pretrained yolov8n model (downloads ~6 MB on first call)."""
    return YoloDetector("yolov8n.pt", conf_threshold=0.05)


def _load_any_test_image() -> np.ndarray:
    """Return the first test image found, or a blank frame."""
    if SAMPLE_IMAGE.exists():
        for f in sorted(SAMPLE_IMAGE.iterdir()):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                return cv2.imread(str(f))
    return np.zeros((640, 640, 3), dtype=np.uint8)


def test_yolo_detector_is_detector_interface(yolo_detector: YoloDetector) -> None:
    assert isinstance(yolo_detector, object)
    assert hasattr(yolo_detector, "detect")
    assert hasattr(yolo_detector, "name")


def test_yolo_detector_name(yolo_detector: YoloDetector) -> None:
    assert "yolo" in yolo_detector.name.lower()


def test_yolo_detector_returns_frame_detections(
    yolo_detector: YoloDetector,
) -> None:
    frame = _load_any_test_image()
    result = yolo_detector.detect(frame, frame_id=0)
    assert isinstance(result, FrameDetections)
    assert result.frame_id == 0


def test_yolo_detect_on_real_image(yolo_detector: YoloDetector) -> None:
    frame = _load_any_test_image()
    result = yolo_detector.detect(frame, frame_id=0)

    for det in result.detections:
        assert isinstance(det, Detection)
        assert det.class_label == "mango"
        assert 0.0 <= det.confidence <= 1.0
        x, y, w, h = det.bbox
        assert w >= 0 and h >= 0
        assert x >= -1 and y >= -1


def test_yolo_detect_sorted_by_confidence(yolo_detector: YoloDetector) -> None:
    frame = _load_any_test_image()
    result = yolo_detector.detect(frame, frame_id=5)
    confs = [d.confidence for d in result.detections]
    assert confs == sorted(confs, reverse=True)


def test_yolo_detector_high_threshold_fewer_detections() -> None:
    frame = _load_any_test_image()
    loose = YoloDetector("yolov8n.pt", conf_threshold=0.05)
    strict = YoloDetector("yolov8n.pt", conf_threshold=0.90)

    r_loose = loose.detect(frame, 0)
    r_strict = strict.detect(frame, 0)

    assert len(r_strict.detections) <= len(r_loose.detections)


def test_yolo_detector_custom_class_names() -> None:
    det = YoloDetector(
        "yolov8n.pt",
        conf_threshold=0.05,
        class_names={0: "fruit"},
    )
    frame = _load_any_test_image()
    result = det.detect(frame, 0)
    for d in result.detections:
        assert d.class_label == "fruit"


def test_yolo_detector_on_blank_frame(yolo_detector: YoloDetector) -> None:
    blank = np.zeros((640, 640, 3), dtype=np.uint8)
    result = yolo_detector.detect(blank, 0)
    assert isinstance(result, FrameDetections)
    assert len(result) == 0


def test_yolo_detector_bbox_format_xywh(yolo_detector: YoloDetector) -> None:
    """Ensure bboxes are (x, y, w, h) not (x1, y1, x2, y2)."""
    frame = _load_any_test_image()
    result = yolo_detector.detect(frame, 0)
    for det in result.detections:
        x, y, w, h = det.bbox
        assert w > 0, "width should be positive"
        assert h > 0, "height should be positive"
