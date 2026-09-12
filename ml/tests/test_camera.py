"""Tests for video sources (OpenCV + synthetic)."""

from __future__ import annotations

import numpy as np
import pytest

from orchardvision_ml.camera import (
    OpenCVVideoSource,
    SyntheticFruit,
    SyntheticScene,
    SyntheticVideoSource,
)


def test_synthetic_source_metadata() -> None:
    source = SyntheticVideoSource()
    info = source.video_info
    assert info.fps == 30.0
    assert info.width == 1280
    assert info.height == 720
    assert info.frame_count == 300


def test_synthetic_source_iterates_all_frames() -> None:
    source = SyntheticVideoSource()
    frames = list(source)
    assert len(frames) == source.video_info.frame_count
    assert frames[0][0] == 0
    assert frames[-1][0] == len(frames) - 1


def test_synthetic_frame_shape_and_dtype() -> None:
    source = SyntheticVideoSource()
    frame_id, frame = source.read()
    assert frame_id == 0
    assert frame.shape == (720, 1280, 3)
    assert frame.dtype == np.uint8
    assert frame.mean() > 0


def test_synthetic_scene_visibility_count() -> None:
    scene = SyntheticScene(
        width=100,
        height=100,
        total_frames=100,
        fruits=(
            SyntheticFruit((10, 10), (20, 20)),
            SyntheticFruit((30, 30), (40, 40), occlusion=(40, 60)),
        ),
    )
    assert scene.visible_count_at(0) == 2
    assert scene.visible_count_at(50) == 1
    assert scene.visible_count_at(70) == 2


def test_synthetic_occlusion_changes_frame_content() -> None:
    fruit = SyntheticFruit((10, 10), (90, 90), occlusion=(5, 10))
    assert fruit.position_at(3, 100) is not None
    assert fruit.position_at(7, 100) is None
    assert fruit.position_at(12, 100) is not None


def test_video_source_context_manager() -> None:
    with SyntheticVideoSource() as source:
        frame_id, frame = source.read()
        assert frame is not None
    # After release, re-reading restarts.
    frame_id, frame = source.read()
    assert frame_id == 0


def test_opencv_source_roundtrip(tmp_path) -> None:
    """Write a tiny video with the synthetic renderer and read it back."""
    import cv2

    out_path = tmp_path / "sample.mp4"
    source = SyntheticVideoSource()
    writer = cv2.VideoWriter(
        str(out_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        source.video_info.fps,
        (source.video_info.width, source.video_info.height),
    )
    for _, frame in source:
        writer.write(frame)
    writer.release()

    assert out_path.exists()
    reader = OpenCVVideoSource(out_path)
    assert reader.video_info.width == 1280
    assert reader.video_info.height == 720
    frames = list(reader)
    assert len(frames) > 0
    reader.release()


def test_opencv_source_invalid_path_raises() -> None:
    with pytest.raises(ValueError):
        OpenCVVideoSource("/nonexistent/file.mp4")
