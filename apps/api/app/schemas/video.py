"""Video, processing-job, and progress response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProcessingJobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    status: str
    stage: str
    progress: float
    inference_mode: str
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    def to_api(self) -> dict:
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


class VideoView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_name: str
    filename: str
    mime_type: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    frame_count: int | None = None
    duration_seconds: float | None = None
    codec: str | None = None
    status: str
    created_at: datetime
    processing_job: ProcessingJobView | None = None


class JobView(BaseModel):
    """Lightweight job payload returned from process-start endpoints."""

    id: str
    status: str
    stage: str
    progress: float
    inference_mode: str
    error: str | None = None


class ProgressResponse(BaseModel):
    """Generic in-flight status payload used while a job runs."""

    job_id: str
    video_id: str
    status: str
    stage: str
    progress: float = Field(ge=0.0, le=100.0)
    message: str | None = None
    inference_mode: str = "mock"


class MultiVideoResponse(BaseModel):
    videos: list[dict]
    total: int


class ProcessRequest(BaseModel):
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    inference_mode: str = Field(default="mock", pattern="^(mock|real)$")
    max_frames: int | None = Field(default=None, ge=1, le=100_000)
