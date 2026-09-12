"""Video upload, listing, retrieval, deletion, and processing."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError, ValidationFailError
from app.models import (
    GLOBAL_SETTINGS_ID,
    AppSettings,
    CameraMotionRecord,
    DetectionRecord,
    FrameTimingRecord,
    IdentityObservation,
    IdentityRecord,
    ProcessingJob,
    ProcessingStatus,
    ReidEvent,
    Track,
    Video,
)
from app.schemas import (
    JobView,
    MultiAnalyticsResponse,
    MultiDetectionResponse,
    MultiFrameTimingResponse,
    MultiIdentityProjectionResponse,
    MultiIdentityResponse,
    MultiMotionResponse,
    MultiObservationResponse,
    MultiReidResponse,
    MultiTrackResponse,
    ProcessRequest,
)
from app.services import (
    MetadataExtractionError,
    PipelineConfig,
    UploadValidationError,
    extract_video_metadata,
    storage_service,
)
from app.services.analytics import compute_video_analytics
from app.services.celery_app import enqueue_video_processing, run_processing_sync
from app.services.embedding_projection import project_prototypes
from app.services.frames import FrameExtractionError, delete_video_frames, extract_frame

router = APIRouter(prefix="/videos", tags=["videos"])


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


def _track_to_identity_map(db: Session, video_id: str) -> dict[int, int]:
    """Map each persisted track id to the identity it was counted under.

    Identity numbering follows the track chain (a reappearance keeps its
    number), so every observation of a track maps to a single identity.
    """
    rows = db.execute(
        select(IdentityObservation.track_id, IdentityObservation.identity_id)
        .where(
            IdentityObservation.video_id == video_id,
            IdentityObservation.track_id.is_not(None),
        )
        .distinct()
    ).all()
    return {track_id: identity_id for track_id, identity_id in rows}


@router.get("/{video_id}/tracks", response_model=MultiTrackResponse)
def list_video_tracks(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return the persisted track trajectories for a processed video."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    rows = db.scalars(
        select(Track).where(Track.video_id == video_id).order_by(Track.track_id)
    ).all()
    identities = _track_to_identity_map(db, video_id)
    tracks = [
        {**r.to_dict(), "identityId": identities.get(r.track_id)} for r in rows
    ]
    return {"tracks": tracks, "total": len(tracks)}


@router.get("/{video_id}/tracks/{track_id}")
def get_video_track(video_id: str, track_id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return a single persisted track trajectory."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    row = db.scalar(select(Track).where(Track.video_id == video_id, Track.track_id == track_id))
    if not row:
        raise NotFoundError("track_not_found", f"Track {track_id} not found for video {video_id}")
    identities = _track_to_identity_map(db, video_id)
    track = {**row.to_dict(), "identityId": identities.get(row.track_id)}
    return {"track": track}


@router.get("/{video_id}/frames/{frame_id}")
def get_video_frame(
    video_id: str,
    frame_id: int,
    db: Annotated[Session, Depends(get_db)],
    width: int | None = None,
) -> Response:
    """Return a single frame from the uploaded video as a JPEG image."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")
    if not video.frame_count or frame_id < 0 or frame_id >= video.frame_count:
        raise NotFoundError("frame_not_found", f"Frame {frame_id} out of range")

    try:
        path = storage_service.resolve(video.filename)
    except FileNotFoundError as exc:
        raise NotFoundError("file_not_found", "Stored video file is missing") from exc
    try:
        data = extract_frame(video, path, frame_id, width)
    except FrameExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=data, media_type="image/jpeg")


@router.get("/{video_id}/file")
def stream_video_file(video_id: str, db: Annotated[Session, Depends(get_db)]) -> FileResponse:
    """Stream the uploaded video file (range requests supported for seeking)."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")
    try:
        path = storage_service.resolve(video.filename)
    except FileNotFoundError as exc:
        raise NotFoundError("file_not_found", "Stored video file is missing") from exc
    return FileResponse(path, media_type=video.mime_type or "video/mp4")


@router.get("/{video_id}/identities", response_model=MultiIdentityResponse)
def list_video_identities(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return the persisted identity prototypes for a processed video."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    rows = db.scalars(
        select(IdentityRecord)
        .where(IdentityRecord.video_id == video_id)
        .order_by(IdentityRecord.identity_id)
    ).all()
    return {"identities": [r.to_dict() for r in rows], "total": len(rows)}


@router.get("/{video_id}/identities/projection", response_model=MultiIdentityProjectionResponse)
def get_video_identity_projection(
    video_id: str,
    method: str = Query(default="tsne", pattern="^(tsne|pca)$"),
    db: Annotated[Session, Depends(get_db)] = None,
) -> dict:
    """Return 2D coordinates per identity prototype for embedding visualization."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    rows = db.scalars(
        select(IdentityRecord)
        .where(IdentityRecord.video_id == video_id)
        .order_by(IdentityRecord.identity_id)
    ).all()
    vectors = [r.prototype for r in rows]
    coordinates = project_prototypes(vectors, method=method)
    points = [
        {
            "x": coordinates[i][0],
            "y": coordinates[i][1],
            "identityId": row.identity_id,
            "quality": row.quality,
            "observationCount": row.observation_count,
            "isConfident": row.is_confident,
        }
        for i, row in enumerate(rows)
    ]
    return {"points": points, "method": method, "total": len(points)}


@router.get("/{video_id}/identities/{identity_id}")
def get_video_identity(
    video_id: str, identity_id: int, db: Annotated[Session, Depends(get_db)]
) -> dict:
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")
    row = db.scalar(
        select(IdentityRecord).where(
            IdentityRecord.video_id == video_id,
            IdentityRecord.identity_id == identity_id,
        )
    )
    if not row:
        raise NotFoundError(
            "identity_not_found", f"Identity {identity_id} not found for video {video_id}"
        )
    return row.to_dict()


@router.get(
    "/{video_id}/identities/{identity_id}/observations",
    response_model=MultiObservationResponse,
)
def list_video_identity_observations(
    video_id: str, identity_id: int, db: Annotated[Session, Depends(get_db)]
) -> dict:
    """Return the per-frame observations merged into one learned identity."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")
    identity = db.scalar(
        select(IdentityRecord).where(
            IdentityRecord.video_id == video_id,
            IdentityRecord.identity_id == identity_id,
        )
    )
    if not identity:
        raise NotFoundError(
            "identity_not_found", f"Identity {identity_id} not found for video {video_id}"
        )

    rows = db.scalars(
        select(IdentityObservation)
        .where(
            IdentityObservation.video_id == video_id,
            IdentityObservation.identity_id == identity_id,
        )
        .order_by(IdentityObservation.frame_id)
    ).all()
    return {"observations": [r.to_dict() for r in rows], "total": len(rows)}


@router.get("/{video_id}/reid-events", response_model=MultiReidResponse)
def list_video_reid_events(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return the re-identification events recovered for a processed video."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    rows = db.scalars(
        select(ReidEvent).where(ReidEvent.video_id == video_id).order_by(ReidEvent.lost_frame_id)
    ).all()
    return {"events": [r.to_dict() for r in rows], "total": len(rows)}


@router.get("/{video_id}/detections", response_model=MultiDetectionResponse)
def list_video_detections(
    video_id: str,
    frame_id: int | None = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> dict:
    """Return persisted detections for a video, optionally for a single frame."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    query = select(DetectionRecord).where(DetectionRecord.video_id == video_id)
    if frame_id is not None:
        query = query.where(DetectionRecord.frame_id == frame_id)
    rows = db.scalars(
        query.order_by(DetectionRecord.frame_id, DetectionRecord.confidence.desc())
    ).all()
    return {"detections": [r.to_dict() for r in rows], "total": len(rows)}


@router.get("/{video_id}/per-frame", response_model=MultiFrameTimingResponse)
def list_video_frame_timings(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return per-frame processing timing telemetry for a processed video."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    rows = db.scalars(
        select(FrameTimingRecord)
        .where(FrameTimingRecord.video_id == video_id)
        .order_by(FrameTimingRecord.frame_id)
    ).all()
    return {"timings": [r.to_dict() for r in rows], "total": len(rows)}


@router.get("/{video_id}/motion", response_model=MultiMotionResponse)
def get_video_motion(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return the latest camera-motion estimate for a video."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    row = db.scalar(select(CameraMotionRecord).where(CameraMotionRecord.video_id == video_id))
    if row is None:
        return {"estimate": None, "compensationApplied": None}
    return {"estimate": row.to_dict(), "compensationApplied": row.compensation_applied}


@router.get("/{video_id}/analytics", response_model=MultiAnalyticsResponse)
def get_video_analytics(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return aggregated analytics for a processed video."""
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")

    summary = compute_video_analytics(db, video)
    if summary["totalFruitDetections"] == 0:
        return {"summary": None}
    return {"summary": summary}


@router.delete("/{video_id}")
def delete_video(video_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    video = db.get(Video, video_id)
    if not video:
        raise NotFoundError("video_not_found", f"Video {video_id} not found")
    storage_service.delete(video.filename)
    delete_video_frames(video_id)
    db.execute(delete(Track).where(Track.video_id == video_id))
    db.execute(delete(DetectionRecord).where(DetectionRecord.video_id == video_id))
    db.execute(delete(CameraMotionRecord).where(CameraMotionRecord.video_id == video_id))
    db.execute(delete(FrameTimingRecord).where(FrameTimingRecord.video_id == video_id))
    db.execute(delete(IdentityRecord).where(IdentityRecord.video_id == video_id))
    db.execute(delete(IdentityObservation).where(IdentityObservation.video_id == video_id))
    db.execute(delete(ReidEvent).where(ReidEvent.video_id == video_id))
    db.execute(delete(ProcessingJob).where(ProcessingJob.video_id == video_id))
    db.delete(video)
    db.commit()
    return {"ok": True}


def _stored_pipeline_defaults(db: Session) -> dict:
    row = db.get(AppSettings, GLOBAL_SETTINGS_ID)
    return row.effective_values() if row else {}


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
    stored = _stored_pipeline_defaults(db)
    config = PipelineConfig(
        inference_mode=request.inference_mode,
        confidence_threshold=request.confidence_threshold
        or float(stored.get("confidenceThreshold", settings.default_confidence_threshold)),
        tracker=request.tracker,
        camera_motion=request.camera_motion or str(stored.get("cameraMotionMode", "static")),
        reid_threshold=request.reid_threshold
        or float(stored.get("reidThreshold", settings.default_reid_threshold)),
        memory_update_rate=request.memory_update_rate
        or float(stored.get("memoryUpdateRate", settings.default_memory_update_rate)),
        tracker_match_threshold=request.tracker_match_threshold
        or float(stored.get("trackerMatchThreshold", settings.default_tracker_match_threshold)),
        tracker_buffer_frames=request.tracker_buffer_frames
        or int(stored.get("trackerBufferFrames", settings.default_tracker_buffer_frames)),
        max_frames=request.max_frames,
        model_path=request.model_path,
        sliced=request.sliced or 0,
    )

    job = ProcessingJob(
        id=uuid4().hex,
        video_id=video.id,
        status=ProcessingStatus.QUEUED,
        inference_mode=config.inference_mode,
        config={
            "confidence_threshold": config.confidence_threshold,
            "tracker": config.tracker,
            "camera_motion": config.camera_motion,
            "reid_threshold": config.reid_threshold,
            "memory_update_rate": config.memory_update_rate,
            "tracker_match_threshold": config.tracker_match_threshold,
            "tracker_buffer_frames": config.tracker_buffer_frames,
            "max_frames": config.max_frames,
            "model_path": config.model_path,
            "sliced": config.sliced,
        },
    )
    db.add(job)
    video.status = "processing"
    db.commit()
    db.refresh(job)

    if settings.celery_broker_url:
        enqueue_video_processing(job.id, video.id, asdict(config))
    else:
        background.add_task(run_processing_sync, job.id, video.id, config)

    return JobView(
        id=job.id,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        inference_mode=job.inference_mode,
    )
