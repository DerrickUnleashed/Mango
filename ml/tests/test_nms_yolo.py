"""Tests for NMS and the YOLO detector adapter."""

from __future__ import annotations

import numpy as np

from orchardvision_ml.detection import YoloDetector
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


class _Tensor:
    """Minimal stand-in for a torch tensor supporting ``.cpu().numpy()``."""

    def __init__(self, value) -> None:
        self._value = np.asarray(value, dtype=float)

    def cpu(self) -> _Tensor:
        return self

    def numpy(self) -> np.ndarray:
        return self._value


class _FakeBoxes:
    def __init__(self, xyxy, conf, cls) -> None:
        self.xyxy = _Tensor(xyxy)
        self.conf = _Tensor(conf)
        self.cls = _Tensor(cls)


class _FakeResult:
    def __init__(self, xyxy, conf, cls) -> None:
        self.boxes = _FakeBoxes(xyxy, conf, cls)


class _FakeModel:
    def __init__(self, result: _FakeResult) -> None:
        self._result = result
        self.predict_calls: list[object] = []

    def predict(self, source, **kwargs):
        self.predict_calls.append(source)
        return [self._result]


def test_yolo_detector_maps_and_filters_results() -> None:
    model = _FakeModel(
        _FakeResult(
            xyxy=[
                (0.0, 0.0, 20.0, 20.0),
                (0.0, 0.0, 20.0, 20.0),
                (200.0, 200.0, 230.0, 230.0),
                (5.0, 5.0, 20.0, 20.0),
            ],
            conf=[0.95, 0.5, 0.8, 0.1],
            cls=[0, 0, 0, 0],
        )
    )
    detector = YoloDetector(model, conf_threshold=0.3)
    frame = np.zeros((100, 300, 3), dtype=np.uint8)
    result = detector.detect(frame, 7)

    assert result.frame_id == 7
    # Only boxes at/above the confidence threshold are returned (NMS stays in
    # ultralytics when weights are used; the adapter filters on confidence).
    assert len(result.detections) == 3
    assert all(d.confidence >= 0.3 for d in result.detections)
    assert result.detections[0].confidence == 0.95
    assert result.detections[0].bbox == (0.0, 0.0, 20.0, 20.0)
    assert result.detections[1].bbox == (200.0, 200.0, 30.0, 30.0)
    assert model.predict_calls[0].shape == frame.shape


def test_yolo_detector_uses_class_names() -> None:
    model = _FakeModel(
        _FakeResult(
            xyxy=[(0.0, 0.0, 10.0, 10.0), (200.0, 200.0, 10.0, 10.0)],
            conf=[0.9, 0.9],
            cls=[0, 1],
        )
    )
    detector = YoloDetector(model, class_names={0: "mango", 1: "worker"})
    result = detector.detect(np.zeros((50, 300, 3), dtype=np.uint8), 0)
    assert len(result.detections) == 2
    assert result.detections[0].class_label == "mango"
    assert result.detections[1].class_label == "worker"


def test_yolo_detector_empty_result() -> None:
    model = _FakeModel(_FakeResult(xyxy=[], conf=[], cls=[]))
    result = YoloDetector(model).detect(np.zeros((50, 50, 3), dtype=np.uint8), 3)
    assert len(result.detections) == 0


def test_yolo_detector_name() -> None:
    model = _FakeModel(_FakeResult(xyxy=[], conf=[], cls=[]))
    model.model_name = "yolov8n"
    assert YoloDetector(model).name == "yolov8n"


def test_yolo_detector_sliced_maps_tiles_to_frame_coords() -> None:
    # Every tile reports the same tile-local box near its top-left corner; with
    # sliced=2 on a 100x100 frame the four tiles shift it to frame coords.
    model = _FakeModel(
        _FakeResult(
            xyxy=[(2.0, 2.0, 12.0, 12.0)],
            conf=[0.9],
            cls=[0],
        )
    )
    detector = YoloDetector(model, sliced=2, slice_overlap=0.0)
    result = detector.detect(np.zeros((100, 100, 3), dtype=np.uint8), 1)

    assert len(model.predict_calls) == 4
    positions = {(d.bbox[0], d.bbox[1]) for d in result.detections}
    assert positions == {(2.0, 2.0), (52.0, 2.0), (2.0, 52.0), (52.0, 52.0)}
    assert {d.bbox[2] for d in result.detections} == {10.0}


def test_yolo_detector_sliced_merges_duplicate_tiles() -> None:
    # Each tile reports the same object twice (low + high conf) in the same
    # spot; the merge NMS must keep only the highest-confidence instance.
    model = _FakeModel(
        _FakeResult(
            xyxy=[(44.0, 2.0, 54.0, 12.0), (44.0, 2.0, 54.0, 12.0)],
            conf=[0.9, 0.6],
            cls=[0, 0],
        )
    )
    detector = YoloDetector(model, sliced=2, slice_overlap=0.0)
    result = detector.detect(np.zeros((100, 100, 3), dtype=np.uint8), 2)

    assert all(d.confidence == 0.9 for d in result.detections)
    assert len(result.detections) == 4
