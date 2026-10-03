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
    message: str | None = None
    config: dict[str, object] | None = None
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
            "message": self.message,
            "config": self.config,
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
    config: dict[str, object] | None = None


class MultiVideoResponse(BaseModel):
    videos: list[dict]
    total: int


class MultiTrackResponse(BaseModel):
    tracks: list[dict]
    total: int


class MultiIdentityResponse(BaseModel):
    identities: list[dict]
    total: int


class MultiIdentityProjectionResponse(BaseModel):
    points: list[dict]
    method: str
    total: int


class MultiReidResponse(BaseModel):
    events: list[dict]
    total: int


class MultiDetectionResponse(BaseModel):
    detections: list[dict]
    total: int


class MultiFrameTimingResponse(BaseModel):
    timings: list[dict]
    total: int


class ProcessRequest(BaseModel):
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    inference_mode: str = Field(default="mock", pattern="^(mock|real)$")
    tracker: str = Field(default="mock", pattern="^(mock|bytetrack|tapnext)$")
    camera_motion: str = Field(default="static", pattern="^(static|drift)$")
    reid_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    memory_update_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    tracker_match_threshold: float | None = Field(default=None, ge=0.0, le=1000.0)
    tracker_buffer_frames: int | None = Field(default=None, ge=1, le=1000)
    max_frames: int | None = Field(default=None, ge=1, le=100_000)
    model_path: str | None = Field(default=None)
    sliced: int | None = Field(default=None, ge=0, le=6)


class MultiMotionResponse(BaseModel):
    estimate: dict | None
    compensationApplied: bool | None = None


class MultiAnalyticsResponse(BaseModel):
    summary: dict | None


class MultiObservationResponse(BaseModel):
    observations: list[dict]
    total: int


class CreateExperimentRequest(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    tracker: str = Field(default="mock", pattern="^(mock|bytetrack)$")
    scenario: str = Field(default="orchard", pattern="^orchard$")
    num_frames: int = Field(default=310, ge=10, le=1000)


class UpdateSettingsRequest(BaseModel):
    values: dict[str, bool | str | int | float]


class SettingsResponse(BaseModel):
    values: dict[str, bool | str | int | float]
    revision: int
    updatedAt: str | None = None


class ExperimentDetailResponse(BaseModel):
    id: str
    name: str
    status: str
    tracker: str
    scenario: str
    numFrames: int
    config: dict | None = None
    metrics: dict | None = None
    error: str | None = None
    createdAt: str | None = None
    completedAt: str | None = None


class ExperimentListResponse(BaseModel):
    experiments: list[ExperimentDetailResponse]
    total: int
