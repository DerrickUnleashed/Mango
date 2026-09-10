"""DB model for persisted pipeline default settings."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base

GLOBAL_SETTINGS_ID = "global"


def _utcnow() -> datetime:
    return datetime.now(UTC)


DEFAULT_SETTINGS: dict = {
    "confidenceThreshold": 0.35,
    "reidThreshold": 0.6,
    "memoryUpdateRate": 0.2,
    "occlusionTimeoutSec": 30,
    "cameraMotionMode": "static",
    "trackerMatchThreshold": 120.0,
    "trackerBufferFrames": 30,
    "showTrackVisualizer": True,
    "showIdentitiesPanel": True,
    "showReidPanel": True,
    "showMotionPanel": True,
    "showAnalyticsPanel": True,
}


class AppSettings(Base):
    """A single persisted row holding the user's pipeline defaults."""

    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=GLOBAL_SETTINGS_ID)
    values: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def effective_values(self) -> dict:
        return {**DEFAULT_SETTINGS, **self.values}

    def to_dict(self) -> dict:
        return {
            "values": self.effective_values(),
            "revision": self.revision,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


__all__ = ["AppSettings", "DEFAULT_SETTINGS", "GLOBAL_SETTINGS_ID"]
