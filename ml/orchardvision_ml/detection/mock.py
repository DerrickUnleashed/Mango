"""Deterministic mock detector for development and testing.

Generates synthetic mango detections with realistic trajectories including
occlusion windows so the full pipeline (tracking → identity → re-ID) can be
exercised without a trained model or a real video.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .base import Detection, Detector, FrameDetections

W = 1280
H = 720

MANGO_SIZE_MIN = 28
MANGO_SIZE_MAX = 52


@dataclass(frozen=True, slots=True)
class MockFruit:
    """A synthetic fruit with its motion and visibility over time."""

    start_frame: int
    end_frame: int
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    occlusion_windows: tuple[tuple[int, int], ...] = ()
    absent_windows: tuple[tuple[int, int], ...] = ()
    size: int = 40

    def position_at(self, frame_id: int) -> tuple[float, float] | None:
        if frame_id < self.start_frame or frame_id > self.end_frame:
            return None
        if any(start <= frame_id <= end for start, end in self.absent_windows):
            return None
        span = max(self.end_frame - self.start_frame, 1)
        t = (frame_id - self.start_frame) / span
        x = self.start_x + (self.end_x - self.start_x) * t
        y = self.start_y + (self.end_y - self.start_y) * t
        x += math.sin(t * 4 * math.pi) * 2.0
        y += math.cos(t * 5 * math.pi) * 1.5
        return (x, y)

    def is_occluded_at(self, frame_id: int) -> bool:
        return any(start <= frame_id <= end for start, end in self.occlusion_windows)


SCENARIO_ORCHARD: tuple[MockFruit, ...] = (
    MockFruit(
        start_frame=0,
        end_frame=300,
        start_x=80,
        start_y=120,
        end_x=1150,
        end_y=300,
        occlusion_windows=((80, 110),),
        absent_windows=((210, 270),),
        size=44,
    ),
    MockFruit(
        start_frame=0,
        end_frame=300,
        start_x=150,
        start_y=360,
        end_x=320,
        end_y=520,
        occlusion_windows=((55, 95),),
        size=36,
    ),
    MockFruit(
        start_frame=0,
        end_frame=300,
        start_x=400,
        start_y=180,
        end_x=410,
        end_y=190,
        size=48,
    ),
    MockFruit(
        start_frame=0,
        end_frame=300,
        start_x=620,
        start_y=300,
        end_x=1160,
        end_y=540,
        occlusion_windows=((40, 82), (240, 255)),
        size=30,
    ),
    MockFruit(
        start_frame=0,
        end_frame=300,
        start_x=900,
        start_y=420,
        end_x=940,
        end_y=430,
        size=42,
    ),
    MockFruit(
        start_frame=20,
        end_frame=300,
        start_x=1100,
        start_y=140,
        end_x=700,
        end_y=560,
        occlusion_windows=((120, 130),),
        absent_windows=((140, 175),),
        size=34,
    ),
    MockFruit(
        start_frame=140,
        end_frame=300,
        start_x=250,
        start_y=170,
        end_x=520,
        end_y=330,
        size=38,
    ),
)


class MockDetector(Detector):
    """Deterministic detector synthesizing an orchard scene.

    The same ``frame_id`` always produces the same detections via a seeded RNG
    and a fixed scenario, keeping tests and demo runs reproducible.
    """

    def __init__(
        self,
        scenario: tuple[MockFruit, ...] = SCENARIO_ORCHARD,
        confidence_range: tuple[float, float] = (0.55, 0.98),
        low_confidence: bool = False,
    ) -> None:
        self._scenario = scenario
        self._conf_range = confidence_range
        self._low_confidence = low_confidence

    @property
    def name(self) -> str:
        return "mock-detector"

    def detect(self, frame: NDArray[np.uint8], frame_id: int) -> FrameDetections:
        rng = np.random.default_rng(seed=1000 + frame_id)
        detections: list[Detection] = []

        for index, fruit in enumerate(self._scenario):
            pos = fruit.position_at(frame_id)
            if pos is None:
                continue
            x, y = pos
            size = fruit.size

            is_occluded = fruit.is_occluded_at(frame_id)
            if is_occluded:
                conf_low, conf_high = self._conf_range[0] * 0.35, self._conf_range[0] * 0.75
                # Partially occluded fruit is still occasionally detected at low confidence
                if rng.uniform() > 0.6:
                    continue
            else:
                conf_low, conf_high = self._conf_range
            confidence = float(rng.uniform(conf_low, conf_high))

            detections.append(
                Detection(
                    bbox=(x - size / 2, y - size / 2, float(size), float(size)),
                    confidence=confidence,
                    class_label="mango",
                    track_id=index,
                )
            )

        detections.sort(key=lambda d: d.confidence, reverse=True)
        return FrameDetections(frame_id=frame_id, detections=detections)
