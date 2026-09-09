"""Video upload, listing, retrieval, deletion, and processing."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError, ValidationFailError
from app.models import ProcessingJob, ProcessingStage, ProcessingStatus, Track, Video
from app.schemas import JobView, MultiTrackResponse, ProcessRequest
from app.services import (
    MetadataExtractionError,
    PipelineConfig,
    UploadValidationError,
    extract_video_metadata,
    job_manager,
    processing_service,
    storage_service,
)

router = APIRouter(prefix="/videos", tags=["videos"])


def _run_processing(job_id: str, video_id: str, config: PipelineConfig) -> None:
    """Background entry point: opens its own DB session for the worker."""
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        video = db.get(Video, video_id)
        if not job or not video:
            return
        try:
            state = job_manager.register(job_id, video_id, config.inference_mode)
        except Exception:
            return
        job.status = ProcessingStatus.RUNNING
        db.commit()
        try:
            processing_service.run(db, video, job, state, config)
            db.commit()
        except Exception:
            db.rollback()
            job.status = ProcessingStatus.FAILED
            job.stage = ProcessingStage.FAILED
            job.error = "Video processing failed"
            db.commit()
        finally:
            job_manager.remove(job_id)


@router.post("", status_code=201)
async def upload_video(
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Video file")],
) -> dict:
    """Upload an orchard video and store its metadata."""
    if not file.filename:
        raise ValidationFailError("missing_filename", "Uploaded file has no filename")

    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise UploadValidationError("File exceeds the maximum allowed size")

    try:
        stored_path = storage_service.save_upload(
            data, file.content_type or "application/octet-stream", file.filename
        )
    except UploadValidationError as exc:
        raise ValidationFailError("invalid_upload", str(exc)) from exc

    try:
        metadata = extract_video_metadata(stored_path)
    except MetadataExtractionError as exc:
        storage_service.delete(stored_path.name)
        raise ValidationFailError("corrupt_video", str(exc)) from exc

    video = Video(
        id=uuid4().hex,
        original_name=file.filename,
        filename=stored_path.name,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        width=metadata.width,
        height=metadata.height,
        fps=metadata.fps,
        frame_count=metadata.frame_count,
        duration_seconds=metadata.duration_seconds,
        codec=metadata.codec,
        status="uploaded",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    return {"video": video.to_dict()}


@router.get("")
def list_videos(db: Annotated[Session, Depends(get_db)]) -> dict:
    total = db.scalar(select(func.count(Video.id))) or 0
    rows = db.scalars(select(Video).order_by(Video.created_at.desc())).all()
    return {"videos": [r.to_dict() for r in rows], "total": total}


@router.get("/{video_id}")
def get_video(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")
    return video.to_dict()


@router.get("/{video_id}/tracks", response_model=MultiTrackResponse)
def list_video_tracks(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return the persisted track trajectories for a processed video."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    rows = db.scalars(
        select(Track).where(Track.video_id == video_id).order_by(Track.track_id)
    ).all()
    return {"tracks": [r.to_dict() for r in rows], "total": len(rows)}


@router.delete("/{video_id}")
def delete_video(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")
    storage_service.delete(video.filename)
    db.execute(delete(Track).where(Track.video_id == video_id))
    db.execute(delete(ProcessingJob).where(ProcessingJob.video_id == video_id))
    db.delete(video)
    db.commit()
    return {"ok": True}


@router.post("/{video_id}/process", response_model=JobView)
def process_video(
    video_id: str,
    background: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    request: ProcessRequest | None = None,
) -> JobView:
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    active_job = db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.video_id == video_id,
            ProcessingJob.status.in_([ProcessingStatus.QUEUED, ProcessingStatus.RUNNING]),
        )
    )
    if active_job:
        raise ConflictError("already_processing", "Video already has an active processing job")

    request = request or ProcessRequest()
    config = PipelineConfig(
        inference_mode=request.inference_mode,
        confidence_threshold=request.confidence_threshold or settings.default_confidence_threshold,
        tracker=request.tracker,
        max_frames=request.max_frames,
    )

    job = ProcessingJob(
        id=uuid4().hex,
        video_id=video.id,
        status=ProcessingStatus.QUEUED,
        inference_mode=config.inference_mode,
        config={
            "confidence_threshold": config.confidence_threshold,
            "tracker": config.tracker,
            "max_frames": config.max_frames,
        },
    )
    db.add(job)
    video.status = "processing"
    db.commit()
    db.refresh(job)

    background.add_task(_run_processing, job.id, video.id, config)

    return JobView(
        id=job.id,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        inference_mode=job.inference_mode,
    )
