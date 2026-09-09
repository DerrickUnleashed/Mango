"""DB model for a runnable evaluation experiment."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ExperimentStatus:
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Experiment(Base):
    """An evaluation run over the mock orchard scenario with a configuration."""

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default=ExperimentStatus.RUNNING, index=True)
    tracker: Mapped[str] = mapped_column(String(32), default="mock")
    scenario: Mapped[str] = mapped_column(String(64), default="orchard")
    num_frames: Mapped[int] = mapped_column(Integer, default=310)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "tracker": self.tracker,
            "scenario": self.scenario,
            "numFrames": self.num_frames,
            "config": self.config,
            "metrics": self.metrics,
            "error": self.error,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
        }


__all__ = ["Experiment", "ExperimentStatus"]
