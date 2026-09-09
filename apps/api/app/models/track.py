"""DB model for persisted short-term tracking results."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Track(Base):
    """A persisted track produced by a processing job.

    ``points`` holds the track trajectory serialized as a list of
    ``{"frameId", "bbox", "confidence", "isOccluded"}`` dicts, matching the
    shared frontend type.
    """

    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("processing_jobs.id"), index=True
    )
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"), index=True)
    track_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="active")
    points: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "jobId": self.job_id,
            "videoId": self.video_id,
            "trackId": self.track_id,
            "status": self.status,
            "points": self.points,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }