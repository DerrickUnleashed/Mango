"""Long-term re-identification abstraction.

A ``ReIdentifier`` watches short-term tracks for loss and reappearance and
owns the long-term identity numbers: a brand-new track receives a new number
unless it is a plausible reappearance of a lost track, in which case it keeps
the original number. Appearance similarity ranks competing reappearance
candidates, but identity numbers are decided by the track chain, not by
embedding clustering.
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
    last_bbox: tuple[float, float, float, float] | None = None
    recovered: bool = False


@dataclass(frozen=True, slots=True)
class ReIdentificationEvent:
    """A fruit reappearing after track loss was matched to a known identity.

    ``candidate_identity_ids`` / ``candidate_scores`` record every competing
    identity that scored at or above the match threshold, so the accepted match
    can be compared against the runners-up.
    """

    track_id: int
    victim_track_id: int
    identity_id: int
    lost_frame_id: int
    reappearance_frame_id: int
    similarity: float
    confidence: float
    accepted: bool
    candidate_identity_ids: tuple[int, ...] = ()
    candidate_scores: tuple[tuple[int, float], ...] = ()


class ReIdentifier(ABC):
    """Abstract re-identification engine."""

    @abstractmethod
    def step(
        self,
        frame_id: int,
        lost_track_ids: list[int],
        embeddings: list[Embedding],
        memory: IdentityMemory | None = None,
    ) -> list[ReIdentificationEvent]:
        """Process one pipeline frame.

        Args:
            frame_id: Zero-based frame index.
            lost_track_ids: Tracks reported lost by the tracker at this frame.
            embeddings: Embeddings produced for this frame (may have
                ``track_id=None`` for unmatched detections).
            memory: Legacy identity memory, retained for composability. The
                chain-numbering re-identifier does not need it.

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
