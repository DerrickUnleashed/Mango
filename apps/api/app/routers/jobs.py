"""Job status endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import ProcessingJob
from app.schemas import ProgressResponse
from app.services.job_manager import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=ProgressResponse)
def get_job_status(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ProgressResponse:
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id))
    if not job:
        raise NotFoundError("job_not_found", f"Job {job_id} not found")

    message: str | None = None
    try:
        state = job_manager.get(job_id)
        stage = state.stage
        progress = state.progress
        message = state.message
    except Exception:
        stage = job.stage
        progress = job.progress

    return ProgressResponse(
        job_id=job.id,
        video_id=job.video_id,
        status=job.status,
        stage=stage,
        progress=progress,
        message=message,
        inference_mode=job.inference_mode,
    )
