"""Mock re-identifier with deterministic memory querying."""

from __future__ import annotations

from orchardvision_ml.identity import Embedding
from orchardvision_ml.memory import Identity, IdentityMemory

from .base import LostTrackInfo, ReIdentificationEvent, ReIdentifier

DEFAULT_MATCH_THRESHOLD = 0.8
DEFAULT_MAX_DISPLACEMENT_PX = 120.0
DEFAULT_MAX_SPEED_PX_PER_FRAME = 45.0
DEFAULT_TOP_K = 5


def _center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x, y, w, h = bbox
    return (x + w / 2.0, y + h / 2.0)


class MockReIdentifier(ReIdentifier):
    """Memory-backed re-identification with motion gating.

    Tracks are unique across a video (ids never reused), so any brand-new
    track whose embedding matches a known identity is a candidate recovery.

    Candidates are ranked by appearance similarity (``top_k``), then filtered:

    1. only identities that still have an unrecovered lost track qualify;
    2. the reappearing track must sit within a motion-plausible radius of where
       the lost track disappeared (the allowed radius grows with the gap, so
       slow drift over long occlusions is permitted).
    """

    def __init__(
        self,
        match_threshold: float = DEFAULT_MATCH_THRESHOLD,
        max_reid_displacement_px: float = DEFAULT_MAX_DISPLACEMENT_PX,
        max_speed_px_per_frame: float = DEFAULT_MAX_SPEED_PX_PER_FRAME,
        top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self.match_threshold = match_threshold
        self.max_reid_displacement_px = max_reid_displacement_px
        self.max_speed_px_per_frame = max_speed_px_per_frame
        self.top_k = max(1, int(top_k))
        self._events: list[ReIdentificationEvent] = []
        self._lost: list[LostTrackInfo] = []
        self._seen_tracks: set[int] = set()
        self._identity_of_track: dict[int, int] = {}
        self._last_bbox_of_track: dict[int, tuple[float, float, float, float] | None] = {}

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
            self._lost.append(
                LostTrackInfo(
                    track_id=lost_id,
                    identity_id=self._identity_of_track.get(lost_id),
                    lost_at_frame=frame_id,
                    last_bbox=self._last_bbox_of_track.get(lost_id),
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
                self._remember_with_bbox(track_id, embedding, memory)
                continue

            ranked = memory.query(embedding, top_k=self.top_k)
            if not ranked or ranked[0][1] < self.match_threshold:
                continue

            best_identity_id = ranked[0][0].identity_id
            self._identity_of_track[track_id] = best_identity_id
            self._last_bbox_of_track[track_id] = embedding.bbox

            victim, identity_id, similarity = self._select_victim(ranked, embedding, frame_id)
            if victim is None:
                continue
            victim.recovered = True
            candidates = [(i, s) for i, s in ranked if s >= self.match_threshold]
            event = ReIdentificationEvent(
                track_id=track_id,
                victim_track_id=victim.track_id,
                identity_id=identity_id,
                lost_frame_id=victim.lost_at_frame,
                reappearance_frame_id=frame_id,
                similarity=similarity,
                confidence=embedding.confidence,
                accepted=True,
                candidate_identity_ids=tuple(c.identity_id for c, _ in candidates),
                candidate_scores=tuple((c.identity_id, float(s)) for c, s in candidates),
            )
            self._events.append(event)
            events.append(event)
        return events

    def _select_victim(
        self,
        ranked: list[tuple[Identity, float]],
        embedding: Embedding,
        frame_id: int,
    ) -> tuple[LostTrackInfo | None, int | None, float]:
        """Pick the first candidate whose identity is recoverable and motion-plausible."""
        for identity, similarity in ranked:
            if similarity < self.match_threshold:
                break
            pending = self._pending_lost(identity.identity_id)
            if pending is None:
                continue
            if not self._motion_allowed(pending, embedding.bbox, frame_id):
                continue
            return pending, identity.identity_id, similarity
        return None, None, 0.0

    def _motion_allowed(
        self,
        lost: LostTrackInfo,
        new_bbox: tuple[float, float, float, float] | None,
        frame_id: int,
    ) -> bool:
        """Gate a reappearance by how far it moved from where it disappeared.

        When either position is unknown the gate passes (nothing to compare).
        Otherwise the allowed displacement grows with the occlusion gap so a
        fruit drifting while occluded is still recovered.
        """
        if lost.last_bbox is None or new_bbox is None:
            return True
        gap = max(frame_id - lost.lost_at_frame, 0)
        cap = self.max_reid_displacement_px + self.max_speed_px_per_frame * gap
        (ax, ay) = _center(lost.last_bbox)
        (bx, by) = _center(new_bbox)
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 <= cap

    def _remember_with_bbox(
        self, track_id: int, embedding: Embedding, memory: IdentityMemory
    ) -> None:
        ranked = memory.query(embedding, top_k=1)
        if ranked and ranked[0][1] >= self.match_threshold:
            self._identity_of_track[track_id] = ranked[0][0].identity_id
        self._last_bbox_of_track[track_id] = embedding.bbox

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
        self._last_bbox_of_track.clear()
