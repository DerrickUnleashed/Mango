"""DB model for per-frame pipeline timing telemetry."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class FrameTimingRecord(Base):
    """Processing wall-clock time for a single frame of a video run.

    ``elapsed_ms`` is the duration of the detection stage for that frame; the
    derived frames-per-second figure is ``1000.0 / elapsed_ms``.
    """

    __tablename__ = "frame_timings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"), index=True)
    frame_id: Mapped[int] = mapped_column(Integer)
    elapsed_ms: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self) -> dict:
        fps = 1000.0 / self.elapsed_ms if self.elapsed_ms > 0 else 0.0
        return {
            "id": self.id,
            "videoId": self.video_id,
            "frameId": self.frame_id,
            "elapsedMs": self.elapsed_ms,
            "fps": fps,
        }
