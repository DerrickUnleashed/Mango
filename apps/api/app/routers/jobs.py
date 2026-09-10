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

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=ProgressResponse)
def get_job_status(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ProgressResponse:
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id))
    if not job:
        raise NotFoundError("job_not_found", f"Job {job_id} not found")

    return ProgressResponse(
        job_id=job.id,
        video_id=job.video_id,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        message=job.message,
        inference_mode=job.inference_mode,
        config=job.config,
    )
