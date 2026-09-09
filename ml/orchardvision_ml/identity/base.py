"""Embedding abstraction for identity learning.

An ``EmbeddingExtractor`` turns a frame plus its detections into fixed-size
appearance vectors. These embeddings are the foundation for both short-term
re-identification (matching fruit across gaps) and the self-supervised
long-term identity memory implemented in later phases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.detection import FrameDetections


@dataclass(slots=True)
class Embedding:
    """An appearance embedding for a single detected object.

    Attributes:
        track_id: Short-term track the detection belongs to (may be None).
        frame_id: Zero-based frame index.
        vector: Unit-norm L2 vector (float32).
        confidence: Detection confidence backing this embedding.
        is_occluded: Whether the object was inside a mock occlusion window.
    """

    track_id: int | None
    frame_id: int
    vector: NDArray[np.float32]
    confidence: float = 0.0
    is_occluded: bool = False

    @property
    def dimension(self) -> int:
        return int(self.vector.shape[0])


class EmbeddingExtractor(ABC):
    """Abstract appearance-embedding extractor."""

    @abstractmethod
    def extract(
        self, frame: NDArray[np.uint8], frame_detections: FrameDetections
    ) -> list[Embedding]:
        """Compute one embedding per detection in the frame.

        Args:
            frame: Image as an ``(H, W, 3)`` uint8 BGR array.
            frame_detections: Detections for this frame.

        Returns:
            One :class:`Embedding` per detection, in detection order.
        """

    @property
    def name(self) -> str:
        """Human-readable extractor identifier (for experiment provenance)."""
        return self.__class__.__name__


def cosine_similarity(a: NDArray[np.float32], b: NDArray[np.float32]) -> float:
    """Cosine similarity between two unit-norm embedding vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) or 1e-9))
