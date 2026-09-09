"""Processing job model for asynchronous video analysis."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProcessingStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingStage:
    UPLOADED = "uploaded"
    EXTRACTING_FRAMES = "extracting_frames"
    DETECTING = "detecting"
    TRACKING = "tracking"
    EMBEDDING = "embedding"
    MEMORY = "memory"
    REID = "reid"
    ANALYTICS = "analytics"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJob(Base):
    """Asynchronous analysis job bound to one video."""

    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"), index=True)

    status: Mapped[str] = mapped_column(String(32), default=ProcessingStatus.QUEUED, index=True)
    stage: Mapped[str] = mapped_column(String(32), default=ProcessingStage.UPLOADED)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    inference_mode: Mapped[str] = mapped_column(String(16), default="mock")

    config: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    video: Mapped[Video] = relationship("Video", back_populates="processing_job")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "videoId": self.video_id,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "inferenceMode": self.inference_mode,
            "error": self.error,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }