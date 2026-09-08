"""In-memory job registry for lightweight asynchronous processing.

This is a minimal job queue for local development: job state lives in memory
while the authoritative row lives in the database. When production scale is
needed, this adapter can be replaced by a Redis/Celery-backed queue without
touching the API surface.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


class JobNotFoundError(Exception):
    pass


class JobAlreadyRunningError(Exception):
    pass


@dataclass
class JobState:
    """In-memory progress state for a running job."""

    job_id: str
    video_id: str
    stage: str = "uploaded"
    progress: float = 0.0
    message: str | None = None
    inference_mode: str = "mock"
    cancelled: bool = False
    listeners: list[Callable[[str, float, str], None]] = field(default_factory=list)

    def update(self, stage: str, progress: float, message: str | None = None) -> None:
        self.stage = stage
        self.progress = progress
        self.message = message
        logger.info("Job %s stage=%s progress=%.1f %s", self.job_id, stage, progress, message or "")
        for listener in self.listeners:
            listener(stage, progress, message)


class JobManager:
    """Tracks live processing jobs in memory."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()

    def register(self, job_id: str, video_id: str, inference_mode: str = "mock") -> JobState:
        with self._lock:
            if job_id in self._jobs:
                raise JobAlreadyRunningError(f"Job {job_id} is already registered")
            state = JobState(job_id=job_id, video_id=video_id, inference_mode=inference_mode)
            self._jobs[job_id] = state
            return state

    def update(self, job_id: str, stage: str, progress: float, message: str | None = None) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state:
                state.update(stage, progress, message)

    def get(self, job_id: str) -> JobState:
        with self._lock:
            state = self._jobs.get(job_id)
            if not state:
                raise JobNotFoundError(f"Job {job_id} not found")
            return state

    def cancel(self, job_id: str) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state:
                state.cancelled = True

    def remove(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def is_running(self, job_id: str) -> bool:
        with self._lock:
            state = self._jobs.get(job_id)
            return state is not None and not state.cancelled


job_manager = JobManager()
