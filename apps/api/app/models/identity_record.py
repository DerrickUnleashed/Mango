"""DB model for persisted long-term identities (identity memory snapshot)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class IdentityRecord(Base):
    """A single identity prototype produced by the identity-memory stage.

    ``prototype`` stores the unit-norm embedding as a JSON list of floats.
    """

    __tablename__ = "identities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"), index=True)
    identity_id: Mapped[int] = mapped_column(Integer)
    quality: Mapped[float] = mapped_column(Float, default=0.0)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    first_frame_id: Mapped[int] = mapped_column(Integer, default=0)
    last_frame_id: Mapped[int] = mapped_column(Integer, default=0)
    last_track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_confident: Mapped[bool] = mapped_column(Boolean, default=False)
    prototype: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "videoId": self.video_id,
            "identityId": self.identity_id,
            "quality": self.quality,
            "observationCount": self.observation_count,
            "firstFrameId": self.first_frame_id,
            "lastFrameId": self.last_frame_id,
            "lastTrackId": self.last_track_id,
            "isConfident": self.is_confident,
            "prototype": self.prototype,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
