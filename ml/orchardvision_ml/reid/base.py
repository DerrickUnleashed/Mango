"""Long-term re-identification abstraction.

A ``ReIdentifier`` watches short-term tracks for loss and reappearance. When a
fruit disappears (track lost) and later shows up again as a brand-new track,
the re-identifier queries identity memory with the new track's appearance
embedding. A confident match against an identity that has a pending (unrecovered)
lost track produces a re-identification event — the fruit was recovered.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from orchardvision_ml.identity import Embedding
from orchardvision_ml.memory import IdentityMemory


@dataclass(slots=True)
class LostTrackInfo:
    """A short-term track that was reported lost by the tracker."""

    track_id: int
    identity_id: int | None
    lost_at_frame: int
    recovered: bool = False


@dataclass(frozen=True, slots=True)
class ReIdentificationEvent:
    """A fruit reappearing after track loss was matched to a known identity."""

    track_id: int
    victim_track_id: int
    identity_id: int
    lost_frame_id: int
    reappearance_frame_id: int
    similarity: float
    confidence: float
    accepted: bool


class ReIdentifier(ABC):
    """Abstract re-identification engine."""

    @abstractmethod
    def step(
        self,
        frame_id: int,
        lost_track_ids: list[int],
        embeddings: list[Embedding],
        memory: IdentityMemory,
    ) -> list[ReIdentificationEvent]:
        """Process one pipeline frame.

        Args:
            frame_id: Zero-based frame index.
            lost_track_ids: Tracks reported lost by the tracker at this frame.
            embeddings: Embeddings produced for this frame (may have
                ``track_id=None`` for unmatched detections).
            memory: The accumulated identity memory to query against.

        Returns:
            Events emitted at this frame.
        """

    @property
    @abstractmethod
    def events(self) -> list[ReIdentificationEvent]:
        """All events emitted so far, in order."""

    @property
    @abstractmethod
    def lost_tracks(self) -> list[LostTrackInfo]:
        """Unrecovered lost tracks still awaiting reappearance."""

    @abstractmethod
    def reset(self) -> None:
        """Clear internal state before processing a video."""

    @property
    def name(self) -> str:
        return self.__class__.__name__
