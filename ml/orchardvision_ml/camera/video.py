"""Video reading for the counting pipeline.

A ``VideoSource`` yields BGR frames sequentially with their zero-based frame
id.  The abstract class keeps the pipeline decoupled from the capture backend
(single video file, live camera, or synthetic frames for testing).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class VideoInfo:
    """Metadata about the source video."""

    fps: float
    width: int
    height: int
    frame_count: int | None


class VideoSource(ABC):
    """Abstract sequential video source."""

    @property
    @abstractmethod
    def video_info(self) -> VideoInfo:
        """Metadata about the source video."""

    @abstractmethod
    def read(self) -> tuple[int, NDArray[np.uint8] | None]:
        """Return ``(frame_id, frame)``; ``frame`` is ``None`` at end of stream."""

    @abstractmethod
    def release(self) -> None:
        """Free any underlying resources."""

    def __enter__(self) -> VideoSource:
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()

    def __iter__(self):
        while True:
            frame_id, frame = self.read()
            if frame is None:
                return
            yield frame_id, frame
