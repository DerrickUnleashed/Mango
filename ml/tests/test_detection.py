"""Tests for the detector interface and mock detector."""

from __future__ import annotations

import numpy as np

from orchardvision_ml.detection import Detection, Detector, FrameDetections, MockDetector
from orchardvision_ml.detection.mock import MockFruit


def test_detection_center_property() -> None:
    det = Detection(bbox=(10.0, 20.0, 40.0, 30.0), confidence=0.9)
    cx, cy = det.center
    assert cx == 30.0
    assert cy == 35.0


def test_frame_detections_length_and_bool() -> None:
    empty = FrameDetections(frame_id=0)
    assert len(empty) == 0
    assert not empty

    det = Detection(bbox=(0, 0, 10, 10), confidence=0.5)
    one = FrameDetections(frame_id=1, detections=[det])
    assert len(one) == 1
    assert one


def test_mock_detector_is_deterministic() -> None:
    detector = MockDetector()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    first = detector.detect(frame, 100)
    second = detector.detect(frame, 100)

    assert len(first) == len(second)
    for a, b in zip(first.detections, second.detections, strict=True):
        assert a.bbox == b.bbox
        assert a.confidence == b.confidence


def test_mock_detector_detects_expected_fruit_count() -> None:
    detector = MockDetector()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    mid = detector.detect(frame, 150)
    # Scenario has 5 fruits visible at frame 150 (2 out of window, 1 occluded-skip possible)
    assert 4 <= len(mid.detections) <= 7
    for det in mid.detections:
        assert det.class_label == "mango"
        assert 0.0 <= det.confidence <= 1.0


def test_mock_detector_respects_occlusion_windows() -> None:
    fruit = MockFruit(
        start_frame=0,
        end_frame=100,
        start_x=0.0,
        start_y=0.0,
        end_x=100.0,
        end_y=0.0,
        occlusion_windows=((50, 60),),
    )
    assert not fruit.is_occluded_at(49)
    assert fruit.is_occluded_at(50)
    assert fruit.is_occluded_at(55)
    assert fruit.is_occluded_at(60)
    assert not fruit.is_occluded_at(61)


def test_mock_fruit_absent_windows_hide_position() -> None:
    fruit = MockFruit(
        start_frame=0,
        end_frame=100,
        start_x=0.0,
        start_y=0.0,
        end_x=100.0,
        end_y=0.0,
        absent_windows=((50, 60),),
    )
    assert fruit.position_at(49) is not None
    assert fruit.position_at(50) is None
    assert fruit.position_at(57) is None
    assert fruit.position_at(60) is None
    assert fruit.position_at(61) is not None


def test_mock_fruit_positions_bounded() -> None:
    fruit = MockFruit(0, 50, 0.0, 0.0, 100.0, 50.0)
    start = fruit.position_at(0)
    end = fruit.position_at(50)
    assert start is not None and end is not None
    assert abs(start[0]) < 1e-6
    assert abs(end[0] - 100.0) < 1e-6
    assert fruit.position_at(51) is None
    assert fruit.position_at(-1) is None


def test_detector_interface_name_defaults_to_class() -> None:
    frame = np.zeros((10, 10, 3), dtype=np.uint8)

    class CustomDetector(Detector):
        def detect(self, frame, frame_id):  # noqa: ARG002, ANN001
            return FrameDetections(frame_id=frame_id)

    detector = CustomDetector()
    assert detector.name == "CustomDetector"
    assert len(detector.detect(frame, 0)) == 0
