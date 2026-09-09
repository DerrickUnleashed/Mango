"""Deterministic in-memory identity memory for development.

Matches fresh embeddings against stored prototypes by cosine similarity,
creates new identities for unmatched observations, and smoothly updates
matched prototypes (confidence-weighted moving average). Low-quality
observations are ignored entirely, mirroring how the production memory will
gate updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from orchardvision_ml.identity import Embedding, cosine_similarity

from .base import Identity, IdentityMemory, moving_average, quality_score

DEFAULT_MATCH_THRESHOLD = 0.7
DEFAULT_MIN_QUALITY = 0.3
DEFAULT_UPDATE_RATE = 0.15


@dataclass(slots=True)
class MockIdentityMemory(IdentityMemory):
    """Greedy prototype-based identity memory."""

    match_threshold: float = DEFAULT_MATCH_THRESHOLD
    min_quality: float = DEFAULT_MIN_QUALITY
    update_rate: float = DEFAULT_UPDATE_RATE

    _identities: dict[int, Identity] = field(default_factory=dict)
    _next_id: int = field(default=1)

    @property
    def name(self) -> str:
        return "mock-memory"

    @property
    def identities(self) -> list[Identity]:
        return sorted(self._identities.values(), key=lambda i: i.identity_id)

    def update(self, embedding: Embedding) -> Identity | None:
        quality = quality_score(embedding.confidence, embedding.is_occluded)
        if quality < self.min_quality:
            return None

        identity, similarity = self._best_match(embedding.vector)
        if identity is not None and similarity >= self.match_threshold:
            identity.prototype = moving_average(
                identity.prototype, embedding.vector, self.update_rate
            )
            identity.quality = 0.9 * identity.quality + 0.1 * quality
            identity.observation_count += 1
            identity.last_frame_id = embedding.frame_id
            identity.last_track_id = embedding.track_id
            return identity

        new_identity = Identity(
            identity_id=self._next_id,
            prototype=embedding.vector.astype(np.float32),
            quality=quality,
            observation_count=1,
            first_frame_id=embedding.frame_id,
            last_frame_id=embedding.frame_id,
            last_track_id=embedding.track_id,
        )
        self._next_id += 1
        self._identities[new_identity.identity_id] = new_identity
        return new_identity

    def query(self, embedding: Embedding, top_k: int = 5) -> list[tuple[Identity, float]]:
        scored = [
            (identity, cosine_similarity(identity.prototype, embedding.vector))
            for identity in self._identities.values()
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def lookup(self, identity_id: int) -> Identity | None:
        return self._identities.get(identity_id)

    def _best_match(self, vector: np.ndarray) -> tuple[Identity | None, float]:
        best_identity: Identity | None = None
        best_similarity = -1.0
        for identity in self._identities.values():
            similarity = cosine_similarity(identity.prototype, vector)
            if similarity > best_similarity:
                best_similarity = similarity
                best_identity = identity
        return best_identity, best_similarity
