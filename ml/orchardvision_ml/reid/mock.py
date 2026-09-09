"""Mock re-identifier with deterministic memory querying."""

from __future__ import annotations

from orchardvision_ml.identity import Embedding
from orchardvision_ml.memory import IdentityMemory

from .base import LostTrackInfo, ReIdentificationEvent, ReIdentifier


class MockReIdentifier(ReIdentifier):
    """Greedy memory-backed re-identification for mock pipelines.

    Tracks are unique across a video (ids never reused), so any brand-new
    track whose embedding matches a known identity is a candidate recovery.
    The match is accepted only when that identity still has an unrecovered
    lost track, splitting the lost track's disappearance from the new
    appearance into a :class:`ReIdentificationEvent`.
    """

    def __init__(self, match_threshold: float = 0.8) -> None:
        self.match_threshold = match_threshold
        self._events: list[ReIdentificationEvent] = []
        self._lost: list[LostTrackInfo] = []
        self._seen_tracks: set[int] = set()
        self._identity_of_track: dict[int, int] = {}

    def step(
        self,
        frame_id: int,
        lost_track_ids: list[int],
        embeddings: list[Embedding],
        memory: IdentityMemory,
    ) -> list[ReIdentificationEvent]:
        for lost_id in lost_track_ids:
            if any(lost.track_id == lost_id for lost in self._lost):
                continue
            identity_id = self._identity_of_track.get(lost_id)
            self._lost.append(
                LostTrackInfo(
                    track_id=lost_id,
                    identity_id=identity_id,
                    lost_at_frame=frame_id,
                )
            )

        events: list[ReIdentificationEvent] = []
        for embedding in embeddings:
            track_id = embedding.track_id
            if track_id is None:
                continue
            first_seen = track_id not in self._seen_tracks
            self._seen_tracks.add(track_id)
            if not first_seen:
                self._remember(track_id, embedding, memory)
                continue

            ranked = memory.query(embedding, top_k=1)
            if not ranked or ranked[0][1] < self.match_threshold:
                continue
            identity_id, similarity = ranked[0][0].identity_id, ranked[0][1]
            self._identity_of_track[track_id] = identity_id

            victim = self._pending_lost(identity_id)
            if victim is None:
                continue
            victim.recovered = True
            event = ReIdentificationEvent(
                track_id=track_id,
                victim_track_id=victim.track_id,
                identity_id=identity_id,
                lost_frame_id=victim.lost_at_frame,
                reappearance_frame_id=frame_id,
                similarity=similarity,
                confidence=embedding.confidence,
                accepted=True,
            )
            self._events.append(event)
            events.append(event)
        return events

    def _remember(self, track_id: int, embedding: Embedding, memory: IdentityMemory) -> None:
        ranked = memory.query(embedding, top_k=1)
        if not ranked or ranked[0][1] < self.match_threshold:
            return
        self._identity_of_track[track_id] = ranked[0][0].identity_id

    def _pending_lost(self, identity_id: int) -> LostTrackInfo | None:
        for lost in self._lost:
            if lost.identity_id == identity_id and not lost.recovered:
                return lost
        return None

    @property
    def events(self) -> list[ReIdentificationEvent]:
        return list(self._events)

    @property
    def lost_tracks(self) -> list[LostTrackInfo]:
        return list(self._lost)

    def reset(self) -> None:
        self._events.clear()
        self._lost.clear()
        self._seen_tracks.clear()
        self._identity_of_track.clear()
