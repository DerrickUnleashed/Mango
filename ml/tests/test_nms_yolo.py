"""Tests for NMS and the YOLO detector adapter."""

from __future__ import annotations

import numpy as np

from orchardvision_ml.detection import YOLODetector
from orchardvision_ml.detection.nms import iou, nms


def test_iou_disjoint_boxes() -> None:
    assert iou((0, 0, 10, 10), (20, 20, 10, 10)) == 0.0


def test_iou_identical_boxes() -> None:
    assert abs(iou((0, 0, 10, 10), (0, 0, 10, 10)) - 1.0) < 1e-9


def test_iou_partial_overlap() -> None:
    # Left box [0,0,10,10], right box [5,0,10,10] => overlap 5x10, union 150.
    expected = 50.0 / 150.0
    assert abs(iou((0.0, 0.0, 10.0, 10.0), (5.0, 0.0, 10.0, 10.0)) - expected) < 1e-9


def test_nms_suppresses_heavy_overlap_only() -> None:
    boxes = [(0.0, 0.0, 10.0, 10.0), (1.0, 1.0, 10.0, 10.0), (50.0, 50.0, 10.0, 10.0)]
    scores = [0.9, 0.4, 0.7]
    kept = nms(boxes, scores, iou_threshold=0.5)
    assert kept == [0, 2]
    # The overlapping low-confidence box is suppressed (IoU 0.68 > 0.5).


def test_nms_keeps_distinct_boxes() -> None:
    boxes = [(i * 30, 0.0, 10.0, 10.0) for i in range(4)]
    scores = [0.8, 0.7, 0.6, 0.5]
    assert nms(boxes, scores) == [0, 1, 2, 3]


def test_nms_empty_input() -> None:
    assert nms([], []) == []


def test_nms_tolerance_keeps_shared_edge() -> None:
    # Touching edge boxes overlap by area 0 => both kept.
    boxes = [(0.0, 0.0, 10.0, 10.0), (10.0, 0.0, 10.0, 10.0)]
    assert nms(boxes, [0.9, 0.8], iou_threshold=0.45) == [0, 1]


class _FakeBoxes:
    def __init__(self, xywh, conf, cls) -> None:
        self.xywh = np.asarray(xywh, dtype=float)
        self.conf = np.asarray(conf, dtype=float)
        self.cls = np.asarray(cls, dtype=int)

    def __len__(self) -> int:
        return len(self.xywh)


class _FakeResult:
    def __init__(self, xywh, conf, cls) -> None:
        self.boxes = _FakeBoxes(xywh, conf, cls)
        self.names = {0: "mango", 1: "worker"}


class _FakeModel:
    def __init__(self, result: _FakeResult) -> None:
        self._result = result
        self.predict_calls: list[np.ndarray] = []

    def predict(self, frame, verbose: bool = False) -> list[_FakeResult]:
        self.predict_calls.append(frame)
        return [self._result]


def test_yolo_detector_maps_and_filters_results() -> None:
    model = _FakeModel(
        _FakeResult(
            xywh=[
                (10.0, 10.0, 20.0, 20.0),
                (8.0, 9.0, 22.0, 20.0),
                (200.0, 200.0, 30.0, 30.0),
                (5.0, 5.0, 15.0, 15.0),
            ],
            conf=[0.95, 0.5, 0.8, 0.1],
            cls=[0, 0, 0, 0],
        )
    )
    detector = YOLODetector(model, confidence_threshold=0.3, iou_threshold=0.5)
    frame = np.zeros((100, 300, 3), dtype=np.uint8)
    result = detector.detect(frame, 7)

    assert result.frame_id == 7
    assert (
        len(result.detections) == 2
    )  # boxes 0 (0.95) and 2 (0.8) kept; 1 suppressed; 3 below conf
    assert all(d.confidence >= 0.3 for d in result.detections)
    assert result.detections[0].confidence == 0.95
    assert result.detections[0].bbox == (10.0, 10.0, 20.0, 20.0)
    assert result.detections[1].bbox == (200.0, 200.0, 30.0, 30.0)
    assert model.predict_calls[0].shape == frame.shape


def test_yolo_detector_applies_class_filter() -> None:
    model = _FakeModel(
        _FakeResult(
            xywh=[(0.0, 0.0, 10.0, 10.0), (200.0, 200.0, 10.0, 10.0)],
            conf=[0.9, 0.9],
            cls=[0, 1],
        )
    )
    detector = YOLODetector(model, class_filter={"mango"})
    result = detector.detect(np.zeros((50, 300, 3), dtype=np.uint8), 0)
    assert len(result.detections) == 1
    assert result.detections[0].class_label == "mango"


def test_yolo_detector_empty_result() -> None:
    model = _FakeModel(_FakeResult(xywh=[], conf=[], cls=[]))
    result = YOLODetector(model).detect(np.zeros((50, 50, 3), dtype=np.uint8), 3)
    assert len(result.detections) == 0


def test_yolo_detector_name() -> None:
    model = _FakeModel(_FakeResult(xywh=[], conf=[], cls=[]))
    assert YOLODetector(model).name == "yolo"
