"""Video and related domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models import ProcessingJob


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Video(Base):
    """A single uploaded orchard video."""

    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(512), index=True)
    filename: Mapped[str] = mapped_column(String(512), unique=True)
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    codec: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    processing_job: Mapped[ProcessingJob | None] = relationship(
        "ProcessingJob",
        back_populates="video",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "originalName": self.original_name,
            "filename": self.filename,
            "mimeType": self.mime_type,
            "sizeBytes": self.size_bytes,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frameCount": self.frame_count,
            "durationSeconds": self.duration_seconds,
            "codec": self.codec,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "processingJob": self.processing_job.to_dict() if self.processing_job else None,
        }
