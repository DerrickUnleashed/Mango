"""Tests for real-vs-mock routing in the processing service.

These tests verify that ``PipelineConfig.inference_mode`` selects the correct
detector/embedder without running heavy inference.  The real components are
only *constructed* here; running a real pipeline end-to-end is exercised by
the ML test suite (and requires a trained weights file).
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest
from orchardvision_ml.detection import MockDetector as MLMockDetector
from orchardvision_ml.detection import YoloDetector
from orchardvision_ml.identity import TorchEmbeddingExtractor

from app.services import DEFAULT_MODEL_PATH
from app.services.processing import (
    MockEmbeddingExtractor,
    PipelineConfig,
    processing_service,
)


def _weights_usable(path: Path) -> bool:
    """True only for a real checkpoint file.

    In CI, ""models/**/*.pt"" weights are checked out as git-lfs pointers (a
    tiny text stub) rather than the actual .pt archive, so existence alone is
    not enough — a pointer would fail to load with pickle errors.
    """
    if not path.exists():
        return False
    try:
        with open(path, "rb") as handle:
            head = handle.read(8)
    except OSError:
        return False
    if head.startswith(b"version"):
        return False
    return path.stat().st_size > 1_000


def test_config_defaults_are_mock() -> None:
    config = PipelineConfig()
    assert config.inference_mode == "mock"
    assert config.max_frames is None
    assert config.model_path is None


def test_default_model_path_points_to_weights() -> None:
    assert DEFAULT_MODEL_PATH is not None
    assert ".pt" in DEFAULT_MODEL_PATH.suffix


def test_mock_mode_builds_mock_detector() -> None:
    config = PipelineConfig(inference_mode="mock")
    detector = processing_service._build_detector(config)
    assert isinstance(detector, MLMockDetector)


@pytest.mark.skipif(
    not _weights_usable(DEFAULT_MODEL_PATH),
    reason="trained YOLO weights not available",
)
def test_real_mode_builds_yolo_detector() -> None:
    config = PipelineConfig(inference_mode="real", confidence_threshold=0.5)
    detector = processing_service._build_detector(config)
    assert isinstance(detector, YoloDetector)
    assert detector._conf == 0.5


@pytest.mark.skipif(
    not _weights_usable(DEFAULT_MODEL_PATH),
    reason="trained YOLO weights not available",
)
def test_real_mode_passes_sliced_grid_to_yolo_detector() -> None:
    config = PipelineConfig(inference_mode="real", sliced=3)
    detector = processing_service._build_detector(config)
    assert isinstance(detector, YoloDetector)
    assert detector._sliced == 3


def test_mock_mode_builds_mock_embedder() -> None:
    config = PipelineConfig(inference_mode="mock")
    embedder = processing_service._build_embedder(config)
    assert isinstance(embedder, MockEmbeddingExtractor)


def test_process_request_accepts_tapnext_tracker() -> None:
    from app.schemas.video import ProcessRequest

    request = ProcessRequest(inference_mode="mock", tracker="tapnext")
    assert request.tracker == "tapnext"
    # The experiment harness stays on the light trackers: no tapnext there.
    with pytest.raises(ValueError):
        from app.schemas.video import CreateExperimentRequest

        CreateExperimentRequest(tracker="tapnext")


def test_tapnext_mode_builds_tapnext_tracker() -> None:
    from orchardvision_ml.tracking import TAPNextTracker

    config = PipelineConfig(
        tracker="tapnext",
        tapnext_checkpoint_path="/some/ckpt.pt",
        tracker_match_threshold=77.0,
        tracker_buffer_frames=11,
    )
    tracker = processing_service._build_tracker(config)
    assert isinstance(tracker, TAPNextTracker)
    assert tracker.supports_frame_input
    assert tracker.checkpoint_path == "/some/ckpt.pt"
    assert tracker.match_threshold_px == 77.0
    assert tracker.buffer_size == 11


class _StubProgressState:
    job_id = "job-1"
    video_id = "vid-1"
    stage = "tracking"
    progress = 0.0
    message: str | None = None
    inference_mode = "mock"

    @property
    def cancelled(self) -> bool:
        return False

    def update(self, stage: str, progress: float, message: str | None = None) -> None:
        self.stage = stage
        self.progress = progress
        self.message = message


class _RecordingTracker:
    """Tracker spy asserting the frame-aware contract in track_frames."""

    supports_frame_input = True
    name = "recording"

    def __init__(self) -> None:
        from orchardvision_ml.tracking.base import TrackResult

        self._result = TrackResult
        self.frames: list = []
        self.update_calls = 0

    def update_frame(self, frame) -> None:
        self.frames.append(frame.copy())

    def update(self, detections):
        self.update_calls += 1
        return self._result(
            frame_id=detections.frame_id,
            active_tracks=[],
            new_track_ids=[],
            lost_track_ids=[],
            total_tracks=0,
        )


def test_frame_aware_tracker_receives_every_frame(
    client, sample_video_bytes: bytes, monkeypatch
) -> None:
    """track_frames feeds raw frames to update_frame for frame-input trackers.

    This is the API-side half of the TAPNext++ integration: the tracker cannot
    run without the pixels, so the pipeline must decode and hand each frame
    over in lockstep with the detection batches (torch-free here — only the
    frame feeding is under test).
    """
    import numpy as np
    from orchardvision_ml.detection import MockDetector as MLMockDetector

    from app.core.database import SessionLocal
    from app.models import Video
    from app.services.storage import storage_service

    response = client.post(
        "/api/videos",
        files={"file": ("tap.mp4", sample_video_bytes, "video/mp4")},
    )
    assert response.status_code == 201
    video_id = response.json()["video"]["id"]

    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        assert video is not None
        source = storage_service.resolve(video.filename)

        cap = cv2.VideoCapture(str(source))
        frames: list = []
        try:
            while len(frames) < 6:
                ok, frame = cap.read()
                assert ok, "sample video shorter than expected"
                frames.append(frame)
        finally:
            cap.release()

        detector = MLMockDetector()
        frame_detections = [detector.detect(f, i) for i, f in enumerate(frames)]
        tracker = _RecordingTracker()
        monkeypatch.setattr(processing_service, "_build_tracker", lambda config: tracker)
        monkeypatch.setattr(processing_service, "_persist_tracks", lambda *a, **k: [])

        summary = processing_service.track_frames(
            video,
            job=None,
            state=_StubProgressState(),
            config=PipelineConfig(),
            frame_detections=frame_detections,
            db=db,
        )
        assert summary["tracker"] == "recording"
        assert tracker.update_calls == 6
        assert len(tracker.frames) == 6
        assert all(np.array_equal(a, b) for a, b in zip(tracker.frames, frames, strict=True))
    finally:
        db.close()


def test_real_mode_with_missing_checkpoint_falls_back_to_torch(tmp_path) -> None:
    config = PipelineConfig(
        inference_mode="real",
        embedding_model_path=str(tmp_path / "does-not-exist.pt"),
    )
    embedder = processing_service._build_embedder(config)
    assert isinstance(embedder, TorchEmbeddingExtractor)


def test_real_mode_prefers_trained_embedder_when_checkpoint_exists(tmp_path, monkeypatch) -> None:
    import orchardvision_ml.identity as identity

    created: dict[str, Path] = {}

    class StubEmbedder:
        def __init__(self, path: Path) -> None:
            created["path"] = Path(path)

    monkeypatch.setattr(identity, "Embedder", StubEmbedder)

    checkpoint = tmp_path / "embedder.pt"
    checkpoint.write_bytes(b"\x00" * 1024)
    config = PipelineConfig(inference_mode="real", embedding_model_path=str(checkpoint))
    embedder = processing_service._build_embedder(config)
    assert isinstance(embedder, StubEmbedder)
    assert created["path"] == checkpoint


@pytest.mark.skipif(
    not Path(DEFAULT_MODEL_PATH).exists(),
    reason="trained model absent; embedder would download weights",
)
def test_real_mode_builds_torch_embedder() -> None:
    config = PipelineConfig(inference_mode="real")
    embedder = processing_service._build_embedder(config)
    assert isinstance(embedder, TorchEmbeddingExtractor)
    assert embedder.backbone_name == "resnet18"
