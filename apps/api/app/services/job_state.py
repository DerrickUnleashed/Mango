"""Database-backed job progress state.

The processing pipeline updates a ``state`` object at each stage. Locally the
state lives in memory (:mod:`app.services.job_manager`); in a distributed
deployment the Celery worker persists the same fields to the ``processing_jobs``
row so the API can report live progress without shared memory.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import ProcessingJob, ProcessingStage

logger = get_logger(__name__)


class ProgressState(Protocol):
    """Structural contract the pipeline expects from its state object."""

    job_id: str
    video_id: str
    stage: str
    progress: float
    message: str | None
    inference_mode: str
    cancelled: bool

    def update(self, stage: str, progress: float, message: str | None = None) -> None: ...


class DbJobState:
    """Progress state backed by the processing job row."""

    def __init__(
        self,
        job_id: str,
        video_id: str,
        db: Session,
        inference_mode: str = "mock",
    ) -> None:
        self.job_id = job_id
        self.video_id = video_id
        self._db = db
        self.stage: str = ProcessingStage.UPLOADED
        self.progress: float = 0.0
        self.message: str | None = None
        self.inference_mode: str = inference_mode

    def update(self, stage: str, progress: float, message: str | None = None) -> None:
        self.stage = stage
        self.progress = progress
        self.message = message
        job = self._current()
        if job is not None:
            job.stage = stage
            job.progress = progress
            job.message = message
            self._db.commit()
        logger.info("Job %s stage=%s progress=%.1f %s", self.job_id, stage, progress, message or "")

    @property
    def cancelled(self) -> bool:
        job = self._current()
        return bool(job is not None and job.cancelled)

    def _current(self) -> ProcessingJob | None:
        return self._db.get(ProcessingJob, self.job_id)
