"""Celery application and the distributed processing task.

The Celery app is only used when ``CELERY_BROKER_URL`` is configured; otherwise
``process_video`` dispatches through Starlette ``BackgroundTasks`` (the local
dev path). The Celery worker and the in-process path both converge on
:func:`run_processing_sync`, so job semantics (DB status/progress) are identical
between the two queues.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from celery import Celery

from app.core.config import settings
from app.models import ProcessingJob, ProcessingStage, ProcessingStatus, Video

_task_name = "orchardvision.process_video"
_celery: Celery | None = None


def get_celery_app() -> Celery:
    """Build (once) the Celery app from current settings."""
    global _celery
    if _celery is None:
        broker = settings.celery_broker_url or "memory://"
        backend = settings.celery_result_backend or "memory://"
        _celery = Celery("orchardvision", broker=broker, backend=backend)
        _celery.conf.update(
            task_always_eager=settings.celery_task_always_eager,
            task_track_started=True,
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            broker_connection_retry_on_startup=True,
            worker_prefetch_multiplier=1,
            worker_max_tasks_per_child=1000,
            task_acks_late=True,
        )
    return _celery


def reset_celery_app() -> None:
    """Discard the cached Celery app (used by tests to reload settings)."""
    global _celery
    _celery = None


def enqueue_video_processing(job_id: str, video_id: str, config: dict[str, Any]) -> None:
    """Dispatch a processing job to the Celery queue."""
    get_celery_app().send_task(
        _task_name,
        kwargs={"job_id": job_id, "video_id": video_id, "config": config},
    )


@get_celery_app().task(name=_task_name)
def run_video_processing(job_id: str, video_id: str, config: dict[str, Any]) -> None:
    """Celery task body — executes the pipeline on a worker."""
    from app.services.processing import PipelineConfig

    run_processing_sync(job_id, video_id, PipelineConfig(**config))


celery_app: Celery = get_celery_app()


def run_processing_sync(job_id: str, video_id: str, config: Any) -> None:
    """Shared worker entrypoint for both the in-process and Celery paths."""
    from app.core.database import SessionLocal
    from app.services.processing import processing_service

    from .job_state import DbJobState

    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        video = db.get(Video, video_id)
        if not job or not video:
            return
        job.status = ProcessingStatus.RUNNING
        job.message = None
        job.config = asdict(config)
        db.commit()
        state = DbJobState(job_id, video_id, db, config.inference_mode)
        try:
            processing_service.run(db, video, job, state, config)
            if state.cancelled:
                job.status = ProcessingStatus.CANCELLED
                job.error = "Processing cancelled"
            db.commit()
        except InterruptedError:
            db.rollback()
            job.status = ProcessingStatus.CANCELLED
            job.error = "Processing cancelled"
            db.commit()
        except Exception:
            db.rollback()
            job.status = ProcessingStatus.FAILED
            job.stage = ProcessingStage.FAILED
            job.error = "Video processing failed"
            db.commit()
