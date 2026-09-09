"""Experiment management endpoints for the evaluation harness."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from io import StringIO
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.models import Experiment, ExperimentStatus
from app.schemas import (
    CreateExperimentRequest,
    ExperimentDetailResponse,
    ExperimentListResponse,
)

router = APIRouter(
    prefix="/experiments",
    tags=["experiments"],
    responses={404: {"description": "Not found"}},
)


def _run_experiment(experiment: Experiment) -> None:
    """Synchronously run the mock scenario evaluation for an experiment."""
    from orchardvision_ml.detection.mock import SCENARIO_ORCHARD
    from orchardvision_ml.evaluation import evaluate_scenario

    try:
        report, _, _ = evaluate_scenario(
            list(SCENARIO_ORCHARD),
            experiment.num_frames,
            tracker=experiment.tracker,
        )
        experiment.status = ExperimentStatus.COMPLETED
        experiment.metrics = report.to_dict()
        experiment.completed_at = datetime.now(UTC)
    except Exception as exc:  # pragma: no cover - defensive
        experiment.status = ExperimentStatus.FAILED
        experiment.error = str(exc)


@router.get("", response_model=ExperimentListResponse)
def list_experiments(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return all evaluation experiments, newest first."""
    rows = db.scalars(select(Experiment).order_by(Experiment.created_at.desc())).all()
    return {"experiments": [e.to_dict() for e in rows], "total": len(rows)}


@router.post("", response_model=ExperimentDetailResponse)
def create_experiment(
    request: CreateExperimentRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Create and immediately run an evaluation experiment."""
    experiment = Experiment(
        id=uuid4().hex,
        name=(request.name or f"{request.tracker}-{request.scenario}").strip(),
        status=ExperimentStatus.RUNNING,
        tracker=request.tracker,
        scenario=request.scenario,
        num_frames=request.num_frames,
        config={
            "tracker": request.tracker,
            "scenario": request.scenario,
            "num_frames": request.num_frames,
        },
    )
    db.add(experiment)
    db.commit()
    _run_experiment(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment.to_dict()


@router.get("/{experiment_id}", response_model=ExperimentDetailResponse)
def get_experiment(experiment_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return one experiment including its metrics."""
    experiment = db.get(Experiment, experiment_id)
    if not experiment:
        raise NotFoundError("experiment_not_found", f"Experiment {experiment_id} not found")
    return experiment.to_dict()


@router.get("/{experiment_id}/export")
def export_experiment(
    experiment_id: str,
    db: Annotated[Session, Depends(get_db)],
    format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
) -> Response:
    """Download one experiment's results as JSON or CSV."""
    experiment = db.get(Experiment, experiment_id)
    if not experiment:
        raise NotFoundError("experiment_not_found", f"Experiment {experiment_id} not found")

    payload = experiment.to_dict()
    if format == "json":
        content = json.dumps(payload, indent=2)
        media_type = "application/json"
    else:
        rows = list(payload["config"].items()) if payload["config"] else []
        rows += [("status", payload["status"]), ("numFrames", payload["numFrames"])]
        if payload["metrics"]:
            rows += [("metric:" + k, v) for k, v in payload["metrics"].items()]
        rows += [("createdAt", payload["createdAt"]), ("completedAt", payload["completedAt"])]
        stream = StringIO()
        writer = csv.writer(stream)
        writer.writerow(["field", "value"])
        writer.writerows(rows)
        content = stream.getvalue()
        media_type = "text/csv"

    filename = f"experiment-{experiment.id}.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Remove one experiment."""
    experiment = db.get(Experiment, experiment_id)
    if not experiment:
        raise NotFoundError("experiment_not_found", f"Experiment {experiment_id} not found")
    if experiment.status == ExperimentStatus.RUNNING:
        raise ConflictError("experiment_running", "Running experiments cannot be deleted")
    db.execute(delete(Experiment).where(Experiment.id == experiment_id))
    db.commit()
    return {"ok": True}


__all__ = ["router"]
