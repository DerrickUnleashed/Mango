"""DB model for the camera-motion estimate of a processed video."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CameraMotionRecord(Base):
    """Most recent camera-motion estimate for a video (one row per video)."""

    __tablename__ = "camera_motion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id"), unique=True, index=True
    )
    source: Mapped[str] = mapped_column(String(32))
    dx_per_frame: Mapped[float] = mapped_column(Float)
    dy_per_frame: Mapped[float] = mapped_column(Float)
    mean_abs_shift: Mapped[float] = mapped_column(Float)
    frames_analyzed: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    compensation_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "videoId": self.video_id,
            "source": self.source,
            "dxPerFrame": self.dx_per_frame,
            "dyPerFrame": self.dy_per_frame,
            "meanAbsShift": self.mean_abs_shift,
            "framesAnalyzed": self.frames_analyzed,
            "confidence": self.confidence,
            "compensationApplied": self.compensation_applied,
        }
