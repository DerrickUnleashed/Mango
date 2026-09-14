"""Tests for real-vs-mock routing in the processing service.

These tests verify that ``PipelineConfig.inference_mode`` selects the correct
detector/embedder without running heavy inference.  The real components are
only *constructed* here; running a real pipeline end-to-end is exercised by
the ML test suite (and requires a trained weights file).
"""

from __future__ import annotations

from pathlib import Path

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
