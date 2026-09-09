"""Deterministic mock appearance embedding for development.

Produces a fixed-length, unit-norm vector per detection that blends coarse
colour statistics of the bounding-box crop with a small, position-seeded
perturbation. Two appearances of the same fruit therefore embed into nearby
vectors (high cosine similarity), while different fruit crop regions differ
enough for re-identification experiments to behave predictably in mock mode.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.detection import Detection, FrameDetections

from .base import Embedding, EmbeddingExtractor

EMBEDDING_DIM = 32
OCCLUSION_CONFIDENCE = 0.35
NOISE_SCALE = 0.15


class MockEmbeddingExtractor(EmbeddingExtractor):
    """Deterministic, dependency-free appearance embedder."""

    def __init__(self, dimension: int = EMBEDDING_DIM, seed: int = 0) -> None:
        self.dimension = dimension
        self.seed = seed

    @property
    def name(self) -> str:
        return "mock-embedder"

    def extract(
        self, frame: NDArray[np.uint8], frame_detections: FrameDetections
    ) -> list[Embedding]:
        embeddings: list[Embedding] = []
        for det in frame_detections.detections:
            vec = self._embed(frame, det)
            embeddings.append(
                Embedding(
                    track_id=det.track_id,
                    frame_id=frame_detections.frame_id,
                    vector=vec,
                    confidence=det.confidence,
                    is_occluded=det.confidence < OCCLUSION_CONFIDENCE,
                )
            )
        return embeddings

    def _embed(self, frame: NDArray[np.uint8], det: Detection) -> NDArray[np.float32]:
        features = self._crop_features(frame, det.bbox)
        features = np.concatenate([features, self._spatial_features(det.bbox)])

        x, y, w, h = det.bbox
        cx, cy = x + w / 2.0, y + h / 2.0
        noise = _seeded_noise(
            f"{self.seed}:{round(cx * 4)}:{round(cy * 4)}", self.dimension - features.shape[0]
        )
        vec = np.concatenate([features, noise]).astype(np.float32)
        norm = np.linalg.norm(vec) or 1.0
        return vec / norm

    @staticmethod
    def _crop_features(
        frame: NDArray[np.uint8], bbox: tuple[float, float, float, float]
    ) -> NDArray:
        h, w = frame.shape[:2]
        x, y, bw, bh = (int(v) for v in bbox)
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(w, x + max(bw, 1)), min(h, y + max(bh, 1))
        crop = frame[y0:y1, x0:x1]
        if crop.size == 0:
            crop = np.full((8, 8, 3), 60, dtype=np.uint8)

        # Vertical split: mean + std colour per half (6 + 6 features).
        # Colours are scaled to [0, 1] so they balance the position noise.
        out: list[float] = []
        boundary = crop.shape[0] // 2
        halves = [crop[:boundary], crop[boundary:]]
        for half in halves:
            if half.size:
                flat = half.reshape(-1, 3).astype(np.float32) / 255.0
                out.extend(flat.mean(axis=0).tolist())
                out.extend(flat.std(axis=0).tolist())
        return np.asarray(out, dtype=np.float32)

    @staticmethod
    def _spatial_features(bbox: tuple[float, float, float, float]) -> NDArray:
        x, y, w, h = bbox
        cx, cy = (x + w / 2.0) / 640.0, (y + h / 2.0) / 360.0
        return np.asarray(
            [cx, cy, np.log(max(w, 1.0)) / 6.0, np.log(max(h, 1.0)) / 6.0], dtype=np.float32
        )


def _seeded_noise(key: str, size: int) -> NDArray:
    """Deterministic pseudo-random noise derived from ``key``."""
    if size <= 0:
        return np.zeros(0, dtype=np.float32)
    seed = _fnv1a(key)
    return np.random.default_rng(seed).normal(0.0, NOISE_SCALE, size=size).astype(np.float32)


def _fnv1a(key: str) -> int:
    """FNV-1a 64-bit hash — deterministic across processes for seeding."""
    value = 0xCBF29CE484222325
    for byte in key.encode("utf-8"):
        value ^= byte
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return value
