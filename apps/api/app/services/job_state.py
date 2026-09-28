"""Database-backed job progress state.

The processing pipeline updates a ``state`` object at each stage. Locally the
state lives in memory; in a distributed deployment the Celery worker persists
the same fields to the ``processing_jobs`` row so the API can report live
progress without shared memory.
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

    def update(self, stage: str, progress: float, message: str | None = None) -> None: ...

    # Declared read-only because that is how the pipeline uses it: it is
    # checked, never assigned. As a plain attribute this Protocol demanded a
    # settable one, which DbJobState's property did not satisfy, even though
    # the implementations are correct.
    @property
    def cancelled(self) -> bool: ...


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
        self.progress = max(self.progress, progress)
        self.message = message
        job = self._current()
        if job is not None:
            job.stage = stage
            job.progress = self.progress
            job.message = message
            self._db.commit()
        logger.info(
            "Job %s stage=%s progress=%.1f %s",
            self.job_id,
            stage,
            self.progress,
            message or "",
        )

    @property
    def cancelled(self) -> bool:
        job = self._current()
        return bool(job is not None and job.cancelled)

    def _current(self) -> ProcessingJob | None:
        return self._db.get(ProcessingJob, self.job_id)
