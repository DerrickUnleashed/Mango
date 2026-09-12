"""Synthetic video source with known ground-truth counts.

Renders a static camera view of moving mango-colored ellipses that occlude
one another.  Every fruit has a known trajectory and visibility windows, so
the pipeline's counting output can be validated before real orchard footage
is available.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from .video import VideoInfo, VideoSource


@dataclass(frozen=True, slots=True)
class SyntheticFruit:
    """A fruit with a straight-line trajectory and optional occlusion window."""

    start: tuple[int, int]
    end: tuple[int, int]
    radius: int = 20
    occlusion: tuple[int, int] | None = None

    def position_at(self, frame_id: int, total_frames: int) -> tuple[int, int] | None:
        if self.occlusion is not None and self.occlusion[0] <= frame_id <= self.occlusion[1]:
            return None
        t = frame_id / max(total_frames - 1, 1)
        x = int(self.start[0] + (self.end[0] - self.start[0]) * t)
        y = int(self.start[1] + (self.end[1] - self.start[1]) * t)
        return x, y


@dataclass(frozen=True, slots=True)
class SyntheticScene:
    """The fixed composition of a synthetic video."""

    width: int = 1280
    height: int = 720
    fps: float = 30.0
    total_frames: int = 300
    fruits: tuple[SyntheticFruit, ...] = ()

    def visible_count_at(self, frame_id: int) -> int:
        return sum(
            1 for fruit in self.fruits if fruit.position_at(frame_id, self.total_frames) is not None
        )


def default_scene(width: int = 1280, height: int = 720) -> SyntheticScene:
    """A 4-mango scene with one fruit occluded mid-video."""
    return SyntheticScene(
        width=width,
        height=height,
        total_frames=300,
        fruits=(
            SyntheticFruit((180, 200), (1050, 320), radius=26),
            SyntheticFruit((250, 480), (400, 540), radius=20),
            SyntheticFruit((600, 300), (900, 300), radius=30, occlusion=(120, 170)),
            SyntheticFruit((1000, 160), (640, 560), radius=22),
        ),
    )


class SyntheticVideoSource(VideoSource):
    """Synthesizes frames for a fixed :class:`SyntheticScene`.

    Args:
        scene: Scene composition. Defaults to a standard 4-fruit scene.
        seed: RNG seed for slight pixel noise.
    """

    def __init__(self, scene: SyntheticScene | None = None, seed: int = 0) -> None:
        self._scene = scene or default_scene()
        self._seed = seed
        self._frame_id = 0

    @property
    def video_info(self) -> VideoInfo:
        return VideoInfo(
            fps=self._scene.fps,
            width=self._scene.width,
            height=self._scene.height,
            frame_count=self._scene.total_frames,
        )

    @property
    def scene(self) -> SyntheticScene:
        return self._scene

    def read(self) -> tuple[int, NDArray[np.uint8] | None]:
        if self._frame_id >= self._scene.total_frames:
            return self._frame_id, None
        frame = self._render_frame(self._frame_id)
        current = self._frame_id
        self._frame_id += 1
        return current, frame

    def release(self) -> None:
        self._frame_id = 0

    def _render_frame(self, frame_id: int) -> NDArray[np.uint8]:
        scene = self._scene
        canvas = np.zeros((scene.height, scene.width, 3), dtype=np.uint8)
        canvas[:] = (45, 70, 40)

        rng = np.random.default_rng(self._seed + frame_id)
        for fruit in scene.fruits:
            pos = fruit.position_at(frame_id, scene.total_frames)
            if pos is None:
                continue
            variance = int(rng.uniform(-25, 25))
            shade = int(np.clip(170 + variance, 100, 225))
            cv2.circle(canvas, pos, int(fruit.radius * 0.8), (shade, shade, shade), -1)

        noise = rng.integers(0, 8, size=canvas.shape, dtype=np.uint8)
        return np.asarray(cv2.add(canvas, noise), dtype=np.uint8)
