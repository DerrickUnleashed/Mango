"""Tests for the camera motion estimation module."""

import pytest

from orchardvision_ml.motion import (
    CameraMotionEstimate,
    MockMotionEstimator,
    StaticMotionEstimator,
)


@pytest.fixture
def bbox() -> tuple[float, float, float, float]:
    return (100.0, 200.0, 40.0, 40.0)


class TestStatic:
    def test_name(self) -> None:
        assert StaticMotionEstimator().name == "static"

    def test_estimate_is_zero_motion(self) -> None:
        estimate = StaticMotionEstimator().estimate(42)
        assert estimate.is_static
        assert estimate.source == "static"
        assert estimate.confidence == 1.0
        assert estimate.frames_analyzed == 43

    def test_compensate_is_identity(self, bbox) -> None:
        assert StaticMotionEstimator().compensate(bbox, 99) == bbox

    def test_decompensate_is_identity(self, bbox) -> None:
        assert StaticMotionEstimator().decompensate(bbox, 99) == bbox


class TestMock:
    def test_constant_per_frame_drift(self) -> None:
        estimator = MockMotionEstimator(dx_per_frame=0.5, dy_per_frame=0.25)
        a = estimator.estimate(10)
        b = estimator.estimate(20)
        assert (a.dx, a.dy) == (0.5, 0.25)
        assert (b.dx, b.dy) == (0.5, 0.25)
        assert a.confidence > 0.9

    def test_compensate_removes_cumulative_drift(self, bbox) -> None:
        estimator = MockMotionEstimator(dx_per_frame=0.5, dy_per_frame=0.25)
        frame_index = 40
        x, y, _, _ = bbox
        shifted = (x + 0.5 * frame_index, y + 0.25 * frame_index, 40.0, 40.0)
        back = estimator.compensate(shifted, frame_index)
        assert back[0] == pytest.approx(x)
        assert back[1] == pytest.approx(y)

    def test_compensate_clamps_out_of_bounds(self) -> None:
        estimator = MockMotionEstimator(dx_per_frame=2.0, dy_per_frame=2.0)
        # Frame 100 wipes out a small bbox near the origin entirely.
        compensated = estimator.compensate((5.0, 5.0, 10.0, 10.0), 100)
        assert compensated[0] == 0.0
        assert compensated[1] == 0.0

    def test_decompensate_restores_raw_coordinates(self, bbox) -> None:
        estimator = MockMotionEstimator(dx_per_frame=0.5, dy_per_frame=0.25)
        frame_index = 40
        x, y, _, _ = bbox
        shifted = (x + 0.5 * frame_index, y + 0.25 * frame_index, 40.0, 40.0)
        back = estimator.compensate(shifted, frame_index)
        raw = estimator.decompensate(back, frame_index)
        assert raw[0] == pytest.approx(x + 0.5 * frame_index)
        assert raw[1] == pytest.approx(y + 0.25 * frame_index)

    def test_decompensate_roundtrips_compensate(self, bbox) -> None:
        estimator = MockMotionEstimator(dx_per_frame=0.5, dy_per_frame=0.2)
        for frame_index in (0, 1, 30, 120):
            compensated = estimator.compensate(bbox, frame_index)
            raw = estimator.decompensate(compensated, frame_index)
            assert raw[0] == pytest.approx(max(0.0, bbox[0]))
            assert raw[1] == pytest.approx(max(0.0, bbox[1]))

    def test_static_flag(self) -> None:
        assert MockMotionEstimator(dx_per_frame=0.0, dy_per_frame=0.0).estimate(0).is_static
        assert not MockMotionEstimator(dx_per_frame=0.1, dy_per_frame=0.0).estimate(0).is_static


def test_estimate_dataclass_defaults() -> None:
    estimate = CameraMotionEstimate()
    assert estimate.is_static
    assert estimate.frames_analyzed == 0
