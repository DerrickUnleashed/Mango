"""Video metadata extraction using OpenCV."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from app.core.logging import get_logger

logger = get_logger(__name__)


class MetadataExtractionError(Exception):
    """Raised when a video cannot be opened or read."""


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float
    codec: str


def extract_video_metadata(path: Path) -> VideoMetadata:
    """Read resolution, frame rate, frame count, and codec from a video file."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise MetadataExtractionError("Video could not be opened (corrupted or unsupported)")

    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        codec_raw = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = (
            "".join(chr((codec_raw >> (8 * i)) & 0xFF) for i in range(4)).strip()
            if codec_raw
            else None
        )
    finally:
        cap.release()

    if width <= 0 or height <= 0:
        raise MetadataExtractionError("Video has invalid dimensions")
    if fps <= 0:
        fps = 30.0
    if frame_count <= 0:
        frame_count = 0

    duration = frame_count / fps if frame_count and fps else 0.0
    logger.info("Metadata extracted: %dx%d @ %.2ffps, %d frames", width, height, fps, frame_count)

    return VideoMetadata(
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        duration_seconds=duration,
        codec=codec or "unknown",
    )
