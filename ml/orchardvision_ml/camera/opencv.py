"""OpenCV-backed video source for real orchard footage."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from .video import VideoInfo, VideoSource


class OpenCVVideoSource(VideoSource):
    """Reads frames from a video file via OpenCV's VideoCapture.

    Args:
        path: Path to the video file (mp4, avi, mov, etc.).
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._cap = cv2.VideoCapture(str(self._path))
        if not self._cap.isOpened():
            raise ValueError(f"Could not open video: {self._path}")

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._info = VideoInfo(
            fps=fps,
            width=width,
            height=height,
            frame_count=count if count > 0 else None,
        )
        self._frame_id = 0

    @property
    def video_info(self) -> VideoInfo:
        return self._info

    def read(self) -> tuple[int, NDArray[np.uint8] | None]:
        ok, frame = self._cap.read()
        if not ok:
            return self._frame_id, None
        current = self._frame_id
        self._frame_id += 1
        return current, np.asarray(frame)

    def release(self) -> None:
        self._cap.release()
