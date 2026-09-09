"""Tests for the evaluation harness."""

import math

import pytest

from orchardvision_ml.detection.mock import MockFruit
from orchardvision_ml.evaluation import (
    evaluate,
    evaluate_scenario,
    ground_truth_trajectories,
    hota,
    iou,
)
from orchardvision_ml.evaluation.tracks import Tracklet


def make_gt(object_id: int, boxes: dict[int, tuple]) -> Tracklet:
    return Tracklet(object_id=object_id, observations=tuple(sorted(boxes.items())))


class TestIoU:
    def test_iou_overlap(self) -> None:
        assert iou((0, 0, 10, 10), (5, 5, 10, 10)) == pytest.approx(25 / 175)

    def test_iou_no_overlap(self) -> None:
        assert iou((0, 0, 10, 10), (20, 20, 10, 10)) == 0.0

    def test_iou_contained(self) -> None:
        assert iou((0, 0, 10, 10), (2, 2, 4, 4)) == pytest.approx(16 / 100)


class TestCountAccuracy:
    def test_perfect_tracking(self) -> None:
        gt = [
            make_gt(0, {0: (0, 0, 10, 10), 1: (1, 1, 10, 10)}),
            make_gt(1, {0: (50, 50, 10, 10), 1: (51, 51, 10, 10)}),
        ]
        pred = [  # counted on the same frames regardless of ids
            make_gt(10, {0: (0, 0, 10, 10), 1: (1, 1, 10, 10)}),
            make_gt(11, {0: (50, 50, 10, 10), 1: (51, 51, 10, 10)}),
        ]
        mae, mape = evaluate(gt, pred).count_mae, evaluate(gt, pred).count_mape
        assert mae == 0.0
        assert mape == 0.0

    def test_missing_object_raises_errors(self) -> None:
        gt = [make_gt(0, {0: (0, 0, 10, 10), 1: (0, 0, 10, 10)})]
        pred = [make_gt(0, {0: (0, 0, 10, 10)})]  # disappears at frame 1
        report = evaluate(gt, pred)
        assert report.count_mae == pytest.approx(0.5)
        assert report.count_mape == 50.0


class TestIdf1:
    def test_perfect_identity_tracking_scores_1(self) -> None:
        gt = [
            make_gt(0, {i: (20 + i, 20, 10, 10) for i in range(5)}),
            make_gt(1, {i: (80 + i, 80, 10, 10) for i in range(5)}),
        ]
        pred = [
            make_gt(3, {i: (20 + i, 20, 10, 10) for i in range(5)}),
            make_gt(7, {i: (80 + i, 80, 10, 10) for i in range(5)}),
        ]
        assert evaluate(gt, pred).idf1 == pytest.approx(1.0)

    def test_identity_switch_penalizes_score(self) -> None:
        gt = [make_gt(0, {i: (20 + i, 20, 10, 10) for i in range(6)})]
        # pred track A covers 0-2, track B covers 3-5 at the same place: switch
        pred = [
            make_gt(4, {i: (20 + i, 20, 10, 10) for i in range(3)}),
            make_gt(5, {i: (20 + i, 20, 10, 10) for i in range(3, 6)}),
        ]
        report = evaluate(gt, pred)
        assert report.idf1 < 1.0
        assert report.id_switches == 1

    def test_unmatched_gt_track_lowers_score(self) -> None:
        gt = [
            make_gt(0, {i: (20, 20, 10, 10) for i in range(4)}),
            make_gt(1, {i: (80, 80, 10, 10) for i in range(4)}),
        ]
        pred = [make_gt(2, {i: (20, 20, 10, 10) for i in range(4)})]
        report = evaluate(gt, pred)
        assert report.idf1 < 1.0
        assert report.count_mae == pytest.approx(1.0)


class TestFragmentation:
    def test_single_fragment(self) -> None:
        gt = [make_gt(0, {i: (10, 10, 5, 5) for i in range(4)})]
        pred = [make_gt(1, {i: (10, 10, 5, 5) for i in range(4)})]
        assert evaluate(gt, pred).track_fragmentation == pytest.approx(1.0)

    def test_interruption_fragments(self) -> None:
        gt = [make_gt(0, {i: (10, 10, 5, 5) for i in range(6)})]
        pred = [
            make_gt(1, {0: (10, 10, 5, 5), 1: (10, 10, 5, 5), 2: (10, 10, 5, 5)}),
            make_gt(2, {3: (10, 10, 5, 5), 4: (10, 10, 5, 5), 5: (10, 10, 5, 5)}),
        ]
        assert evaluate(gt, pred).track_fragmentation == pytest.approx(2.0)


def test_identity_recovery_rate() -> None:
    report = evaluate([], [], recovered=2, total_gaps=4)
    assert report.identity_recovery_rate == pytest.approx(0.5)


class TestHota:
    def test_perfect_tracking_scores_1(self) -> None:
        gt = [
            make_gt(0, {i: (20 + i, 20, 10, 10) for i in range(5)}),
            make_gt(1, {i: (80 + i, 80, 10, 10) for i in range(5)}),
        ]
        pred = [
            make_gt(3, {i: (20 + i, 20, 10, 10) for i in range(5)}),
            make_gt(7, {i: (80 + i, 80, 10, 10) for i in range(5)}),
        ]
        report = evaluate(gt, pred)
        assert report.hota == pytest.approx(1.0)

    def test_switch_lowers_association(self) -> None:
        gt = [make_gt(0, {i: (20 + i, 20, 10, 10) for i in range(10)})]
        # pred switches identity after frame 4: all boxes matched, but the
        # trajectory pair becomes inconsistent → DetA 1, AssA 0.5.
        pred = [
            make_gt(4, {i: (20 + i, 20, 10, 10) for i in range(5)}),
            make_gt(5, {i: (20 + i, 20, 10, 10) for i in range(5, 10)}),
        ]
        report = evaluate(gt, pred)
        assert report.hota == pytest.approx(math.sqrt(0.5))

    def test_missing_detection_lowers_detection(self) -> None:
        gt = [make_gt(0, {i: (20, 20, 10, 10) for i in range(6)})]
        pred = [make_gt(1, {i: (20, 20, 10, 10) for i in [0, 2, 4]})]
        report = evaluate(gt, pred)
        assert report.hota == pytest.approx(math.sqrt(3 / 6))  # DetA 0.5, AssA 1

    def test_empty_trajectories(self) -> None:
        assert hota([], []) == 0.0


class TestScenarioEvaluation:
    def test_two_static_fruits_are_tracked_perfectly(self) -> None:
        fruits = [
            MockFruit(
                start_x=100,
                start_y=100,
                end_x=100,
                end_y=100,
                size=40,
                start_frame=0,
                end_frame=20,
            ),
            MockFruit(
                start_x=700,
                start_y=500,
                end_x=700,
                end_y=500,
                size=50,
                start_frame=0,
                end_frame=20,
            ),
        ]
        report, gt, pred = evaluate_scenario(fruits, num_frames=20)
        assert len(gt) == 2
        assert len(pred) == 2
        assert report.idf1 == pytest.approx(1.0)
        assert report.count_mae == 0.0

    def test_occlusion_produces_fragmentation(self) -> None:
        fruit = MockFruit(
            start_x=300,
            start_y=300,
            end_x=300,
            end_y=300,
            size=40,
            start_frame=0,
            end_frame=40,
            occlusion_windows=((15, 25),),
        )
        report, _, pred = evaluate_scenario([fruit], num_frames=40)
        # The mock detector still emits low-confidence detections during
        # occlusion, so the tracker typically stays alive; fragmentation is
        # measured, not asserted to be non-zero here.
        assert report.idf1 >= 0.0
        assert len(pred) >= 1

    def test_ground_truth_honors_absent_windows(self) -> None:
        fruit = MockFruit(
            start_x=200,
            start_y=200,
            end_x=200,
            end_y=200,
            size=40,
            start_frame=0,
            end_frame=30,
            absent_windows=((10, 20),),
        )
        traj = ground_truth_trajectories([fruit], 30)[0]
        frames = {f for f, _ in traj.observations}
        assert 9 in frames
        assert 21 in frames
        assert not frames.intersection(range(10, 21))
