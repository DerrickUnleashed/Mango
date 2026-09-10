"""On-demand frame extraction from stored uploads.

Frames are read with OpenCV, encoded as JPEG, and cached under the upload
directory so repeated scrubbing does not re-decode the source video.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from app.core.config import settings
from app.core.logging import get_logger
from app.models import Video

logger = get_logger(__name__)

MAX_ENCODE_QUALITY = 95


class FrameExtractionError(Exception):
    """Raised when a requested frame cannot be read or encoded."""


def _frame_cache_dir(video_id: str) -> Path:
    return settings.upload_dir / "frames" / video_id


def _cached_frame_path(video_id: str, frame_id: int) -> Path:
    return _frame_cache_dir(video_id) / f"{frame_id:06d}.jpg"


def extract_frame(video: Video, source: Path, frame_id: int, width: int | None = None) -> bytes:
    """Return a frame as JPEG bytes, reading from cache when possible.

    ``frame_id`` must already be validated against the video's frame count by
    the caller. ``width`` optionally downscales to fit a thumbnail width.
    """
    if frame_id < 0:
        raise FrameExtractionError("frame index out of range")

    cached = _cached_frame_path(video.id, frame_id)
    if cached.exists() and width is None:
        return cached.read_bytes()

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise FrameExtractionError("video source could not be opened")

    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ok, frame = cap.read()
        if not ok or frame is None:
            raise FrameExtractionError(f"could not read frame {frame_id}")
    finally:
        cap.release()

    if width is not None and width > 0:
        scale = width / frame.shape[1]
        height = max(1, int(round(frame.shape[0] * scale)))
        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, MAX_ENCODE_QUALITY])
    if not ok:
        raise FrameExtractionError(f"could not encode frame {frame_id}")

    data = encoded.tobytes()
    if width is None:
        _frame_cache_dir(video.id).mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    return data


def delete_video_frames(video_id: str) -> None:
    """Remove the cached frames for a video."""
    directory = _frame_cache_dir(video_id)
    if directory.exists():
        for entry in directory.iterdir():
            entry.unlink(missing_ok=True)
        directory.rmdir()
        logger.info("Removed cached frames for video %s", video_id)


__all__ = ["FrameExtractionError", "delete_video_frames", "extract_frame"]
