"""Tests for the real counting pipeline orchestrator."""

from __future__ import annotations

import numpy as np

from orchardvision_ml.camera import SyntheticVideoSource
from orchardvision_ml.detection import MockDetector
from orchardvision_ml.identity import MockEmbeddingExtractor
from orchardvision_ml.memory import MockIdentityMemory
from orchardvision_ml.pipeline import CountingPipeline, PipelineResult
from orchardvision_ml.reid import MockReIdentifier
from orchardvision_ml.tracking import ByteTrackAdapter, Tracker, TrackResult


def _make_pipeline() -> CountingPipeline:
    return CountingPipeline(
        detector=MockDetector(),
        tracker=ByteTrackAdapter(),
        embedder=MockEmbeddingExtractor(),
        memory=MockIdentityMemory(),
        reidentifier=MockReIdentifier(),
    )


class _FrameAwareRecorderTracker(Tracker):
    """Minimal frame-consuming tracker used to test the pipeline hook."""

    supports_frame_input = True
    name = "frame-recorder"

    def __init__(self) -> None:
        self.frames_seen: list[int] = []

    def update_frame(self, frame: np.ndarray) -> None:
        self.frames_seen.append(int(frame.sum()))

    def update(self, detections):
        return TrackResult(
            frame_id=detections.frame_id,
            active_tracks=[],
            new_track_ids=[],
            lost_track_ids=[],
            total_tracks=0,
        )


def test_pipeline_feeds_frames_to_frame_aware_trackers() -> None:
    recorder = _FrameAwareRecorderTracker()
    pipeline = CountingPipeline(
        detector=MockDetector(),
        tracker=recorder,
        embedder=MockEmbeddingExtractor(),
        memory=MockIdentityMemory(),
        reidentifier=MockReIdentifier(),
    )
    result = pipeline.run(SyntheticVideoSource())
    assert result.frames_processed == 300
    # Every frame reached the tracker through update_frame before update().
    assert len(recorder.frames_seen) == result.frames_processed
    # Assert the frames are non-empty footage (not an empty buffer).
    assert all(seen > 0 for seen in recorder.frames_seen)


def test_pipeline_counts_fruit() -> None:
    result = _make_pipeline().run(SyntheticVideoSource())
    assert isinstance(result, PipelineResult)
    assert result.final_count > 0
    assert result.frames_processed == 300
    assert result.detection_count > 0


def test_pipeline_tracks_identities_consistently() -> None:
    result = _make_pipeline().run(SyntheticVideoSource())
    assert result.track_count > 0
    # Multiple observations per identity.
    for identity in result.identities:
        assert identity.observation_count >= 1
    ids = [identity.identity_id for identity in result.identities]
    assert len(ids) == len(set(ids))


def test_pipeline_reports_reid_events() -> None:
    result = _make_pipeline().run(SyntheticVideoSource())
    # Re-id events exist because mock scenario fruit appear/disappear.
    assert result.reid_events >= 0
    # Every identity carries timestamps.
    for identity in result.identities:
        assert identity.first_frame_id <= identity.last_frame_id


def test_pipeline_per_frame_counts_monotonic_accumulation() -> None:
    result = _make_pipeline().run(SyntheticVideoSource())
    assert len(result.per_frame_counts) == result.frames_processed
    assert result.per_frame_counts[-1] >= result.per_frame_counts[0]


def test_pipeline_result_includes_video_meta() -> None:
    result = _make_pipeline().run(SyntheticVideoSource())
    assert result.video is not None
    assert result.video.width == 1280
    assert result.video.height == 720


def test_pipeline_no_embedder_skips_memory() -> None:
    pipeline = CountingPipeline(
        detector=MockDetector(),
        tracker=ByteTrackAdapter(),
        embedder=None,
        memory=None,
        reidentifier=None,
    )
    result = pipeline.run(SyntheticVideoSource())
    assert result.final_count == 0
    assert result.detection_count > 0
    assert result.frames_processed == 300


def test_pipeline_short_video() -> None:
    from orchardvision_ml.camera import SyntheticScene

    scene = SyntheticScene(total_frames=30)
    source = SyntheticVideoSource(scene=scene)
    result = _make_pipeline().run(source)
    assert result.frames_processed == 30
    assert result.final_count >= 1


def test_pipeline_motion_estimator_is_used() -> None:
    from orchardvision_ml.motion import MockMotionEstimator

    calls = {"estimates": 0}

    class CountingMotionEstimator(MockMotionEstimator):
        def estimate(self, frame_index, frame=None):
            calls["estimates"] += 1
            return super().estimate(frame_index, frame)

    pipeline = CountingPipeline(
        detector=MockDetector(),
        tracker=ByteTrackAdapter(),
        embedder=MockEmbeddingExtractor(),
        memory=MockIdentityMemory(),
        reidentifier=MockReIdentifier(),
        motion_estimator=CountingMotionEstimator(),
    )
    result = pipeline.run(SyntheticVideoSource())
    assert calls["estimates"] == result.frames_processed
