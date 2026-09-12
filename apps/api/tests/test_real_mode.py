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
    not Path(DEFAULT_MODEL_PATH).exists(),
    reason="trained YOLO weights not available",
)
def test_real_mode_builds_yolo_detector() -> None:
    config = PipelineConfig(inference_mode="real", confidence_threshold=0.5)
    detector = processing_service._build_detector(config)
    assert isinstance(detector, YoloDetector)
    assert detector._conf == 0.5


def test_real_mode_passes_sliced_grid_to_yolo_detector() -> None:
    config = PipelineConfig(inference_mode="real", sliced=3)
    detector = processing_service._build_detector(config)
    assert isinstance(detector, YoloDetector)
    assert detector._sliced == 3


def test_mock_mode_builds_mock_embedder() -> None:
    config = PipelineConfig(inference_mode="mock")
    embedder = processing_service._build_embedder(config)
    assert isinstance(embedder, MockEmbeddingExtractor)


@pytest.mark.skipif(
    not Path(DEFAULT_MODEL_PATH).exists(),
    reason="trained model absent; embedder would download weights",
)
def test_real_mode_builds_torch_embedder() -> None:
    config = PipelineConfig(inference_mode="real")
    embedder = processing_service._build_embedder(config)
    assert isinstance(embedder, TorchEmbeddingExtractor)
    assert embedder.backbone_name == "resnet18"
