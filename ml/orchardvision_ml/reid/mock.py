"""Mock re-identifier with deterministic track-chain identity numbering.

Identity numbers are assigned per track chain, not by pixel similarity:

  * a brand-new track receives the lowest unused identity number, unless it is
    a motion- and appearance-plausible reappearance of a lost track, in which
    case it keeps that identity's number (``renumber same on re-appear``);
  * while a track is live its identity never changes, so two boxes visible at
    the same time can never share an identity number;
  * an identity's number equals the order in which it was first seen.

Appearance similarity is still recorded (and used to rank competing
reappearance candidates), but identity numbers are owned by the re-identifier
itself rather than by clustering embeddings.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.identity import Embedding, cosine_similarity
from orchardvision_ml.memory import IdentityMemory

from .base import LostTrackInfo, ReIdentificationEvent, ReIdentifier

DEFAULT_MATCH_THRESHOLD = 0.8
DEFAULT_MAX_DISPLACEMENT_PX = 120.0
DEFAULT_MAX_SPEED_PX_PER_FRAME = 45.0
DEFAULT_TOP_K = 5


def _center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x, y, w, h = bbox
    return (x + w / 2.0, y + h / 2.0)


class MockReIdentifier(ReIdentifier):
    """Track-chain re-identifier with motion-gated reappearance linking.

    Tracks are unique across a video (ids never reused), so any brand-new
    track is either the first sighting of a mango or a recovery of a track
    that was previously reported lost.

    Recovery candidates are ranked by appearance similarity, then filtered:

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
        self._next_identity = 1
        self._profiles: dict[int, NDArray[np.float32]] = {}
        self._profile_count: dict[int, int] = {}

    def step(
        self,
        frame_id: int,
        lost_track_ids: list[int],
        embeddings: list[Embedding],
        memory: IdentityMemory | None = None,
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
                identity_id = self._identity_of_track.get(track_id)
                if identity_id is not None:
                    self._update_profile(identity_id, embedding.vector)
                self._last_bbox_of_track[track_id] = embedding.bbox
                continue

            ranked = self._query(embedding, self.top_k)
            victim, identity_id, similarity = self._select_victim(ranked, embedding, frame_id)
            if victim is None:
                identity_id = self._next_identity
                self._next_identity += 1

            self._identity_of_track[track_id] = identity_id
            self._last_bbox_of_track[track_id] = embedding.bbox
            self._update_profile(identity_id, embedding.vector)

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
                candidate_identity_ids=tuple(c for c, _ in candidates),
                candidate_scores=tuple(candidates),
            )
            self._events.append(event)
            events.append(event)
        return events

    def identity_for_track(self, track_id: int) -> int | None:
        """The identity number assigned to ``track_id`` (``None`` if unknown)."""
        return self._identity_of_track.get(track_id)

    def _query(self, embedding: Embedding, top_k: int) -> list[tuple[int, float]]:
        scored = [
            (
                identity_id,
                float(cosine_similarity(profile, embedding.vector)),
            )
            for identity_id, profile in self._profiles.items()
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def _select_victim(
        self,
        ranked: list[tuple[int, float]],
        embedding: Embedding,
        frame_id: int,
    ) -> tuple[LostTrackInfo | None, int | None, float]:
        """Pick the first candidate whose identity is recoverable and motion-plausible."""
        for identity_id, similarity in ranked:
            if similarity < self.match_threshold:
                break
            pending = self._pending_lost(identity_id)
            if pending is None:
                continue
            if not self._motion_allowed(pending, embedding.bbox, frame_id):
                continue
            return pending, identity_id, similarity
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

    def _pending_lost(self, identity_id: int) -> LostTrackInfo | None:
        for lost in self._lost:
            if lost.identity_id == identity_id and not lost.recovered:
                return lost
        return None

    def _update_profile(self, identity_id: int, vector: NDArray[np.float32]) -> None:
        """Blend a fresh observation into an identity's appearance profile."""
        if identity_id not in self._profiles:
            self._profiles[identity_id] = vector.astype(np.float32)
            self._profile_count[identity_id] = 1
            return
        count = self._profile_count[identity_id]
        blended = (self._profiles[identity_id] * count + vector) / (count + 1)
        norm = float(np.linalg.norm(blended)) or 1.0
        self._profiles[identity_id] = (blended / norm).astype(np.float32)
        self._profile_count[identity_id] = count + 1

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
        self._profiles.clear()
        self._profile_count.clear()
        self._next_identity = 1
