"""DB model for persisted re-identification events."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ReidEvent(Base):
    """A fruit reappearance matched to a known identity after track loss."""

    __tablename__ = "reid_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"), index=True)
    track_id: Mapped[int] = mapped_column(Integer)
    victim_track_id: Mapped[int] = mapped_column(Integer)
    identity_id: Mapped[int] = mapped_column(Integer)
    lost_frame_id: Mapped[int] = mapped_column(Integer)
    reappearance_frame_id: Mapped[int] = mapped_column(Integer)
    similarity: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    accepted: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "videoId": self.video_id,
            "trackId": self.track_id,
            "victimTrackId": self.victim_track_id,
            "identityId": self.identity_id,
            "lostFrameId": self.lost_frame_id,
            "reappearanceFrameId": self.reappearance_frame_id,
            "similarity": self.similarity,
            "confidence": self.confidence,
            "accepted": self.accepted,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
