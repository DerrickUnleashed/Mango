"""DB model for per-observation identity history."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class IdentityObservation(Base):
    """One embedding merged into a learned identity (a single observation)."""

    __tablename__ = "identity_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"), index=True)
    identity_id: Mapped[int] = mapped_column(Integer, index=True)
    frame_id: Mapped[int] = mapped_column(Integer)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox: Mapped[list] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    is_occluded: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "videoId": self.video_id,
            "identityId": self.identity_id,
            "frameId": self.frame_id,
            "trackId": self.track_id,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "isOccluded": self.is_occluded,
            "qualityAfter": self.quality_after,
        }
