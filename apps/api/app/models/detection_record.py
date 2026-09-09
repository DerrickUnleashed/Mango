"""DB model for persisted per-frame detections."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DetectionRecord(Base):
    """A single detection at a given frame, linked to its short-term track."""

    __tablename__ = "detections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"), index=True)
    frame_id: Mapped[int] = mapped_column(Integer)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox: Mapped[list] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    class_label: Mapped[str] = mapped_column(String(32), default="mango")
    is_occluded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "videoId": self.video_id,
            "frameId": self.frame_id,
            "trackId": self.track_id,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "classLabel": self.class_label,
            "isOccluded": self.is_occluded,
        }
