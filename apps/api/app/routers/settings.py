"""Settings endpoints for persisted pipeline defaults."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import DEFAULT_SETTINGS, GLOBAL_SETTINGS_ID, AppSettings
from app.schemas import SettingsResponse, UpdateSettingsRequest

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)


def _row(db: Session) -> AppSettings:
    row = db.get(AppSettings, GLOBAL_SETTINGS_ID)
    if row is None:
        row = AppSettings(id=GLOBAL_SETTINGS_ID, values={})
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=SettingsResponse)
def get_settings(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return effective pipeline defaults (stored values over defaults)."""
    return _row(db).to_dict()


@router.put("", response_model=SettingsResponse)
def update_settings(
    request: UpdateSettingsRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Merge partial updates into the persisted settings row."""
    row = _row(db)
    known = set(DEFAULT_SETTINGS)
    updates = {k: v for k, v in request.values.items() if k in known}
    merged = {**row.effective_values(), **updates}
    row.values = {**row.values, **updates}
    row.revision += 1
    db.commit()
    db.refresh(row)
    return {"values": merged, "revision": row.revision,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None}


__all__ = ["router"]
