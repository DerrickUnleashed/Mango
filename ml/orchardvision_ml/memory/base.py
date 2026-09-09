"""Identity memory abstraction.

A memory stores one prototype embedding per long-term fruit identity and
updates that prototype incrementally from fresh observations. Updates are
quality-aware (low-confidence and occluded observations are suppressed) and
prototypes evolve as a confidence-weighted moving average, giving
re-identification a stable target to match against after track loss.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.identity import Embedding


@dataclass(slots=True)
class Identity:
    """A long-term identity backed by a prototype embedding."""

    identity_id: int
    prototype: NDArray[np.float32]
    quality: float = 0.0
    observation_count: int = 0
    first_frame_id: int = 0
    last_frame_id: int = 0
    last_track_id: int | None = None

    @property
    def is_confident(self) -> bool:
        return self.observation_count >= 3 and self.quality >= 0.5


def quality_score(confidence: float, is_occluded: bool = False, base: float = 1.0) -> float:
    """Quality in ``[0, 1]`` penalizing low confidence and occlusion."""
    score = confidence * base
    if is_occluded:
        score *= 0.55
    return float(min(1.0, max(0.0, score)))


def moving_average(
    prototype: NDArray[np.float32],
    observation: NDArray[np.float32],
    rate: float,
) -> NDArray[np.float32]:
    """Confidence-weighted moving-average blend, renormalized to unit norm."""
    blended = (1.0 - rate) * prototype + rate * observation
    norm = np.linalg.norm(blended) or 1.0
    return (blended / norm).astype(np.float32)


class IdentityMemory(ABC):
    """Abstract quality-aware identity memory."""

    @abstractmethod
    def update(self, embedding: Embedding) -> Identity | None:
        """Ingest an observation, creating/updating an identity.

        Returns the affected identity, or ``None`` when the observation was
        suppressed (quality below threshold).
        """

    @abstractmethod
    def query(self, embedding: Embedding, top_k: int = 5) -> list[tuple[Identity, float]]:
        """Rank stored identities by cosine similarity to the embedding."""

    @abstractmethod
    def lookup(self, identity_id: int) -> Identity | None:
        """Fetch a single identity by id."""

    @property
    @abstractmethod
    def identities(self) -> list[Identity]:
        """All identities currently retained in memory."""

    @property
    def name(self) -> str:
        return self.__class__.__name__
