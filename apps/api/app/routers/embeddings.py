"""Cross-video embedding aggregation and projection."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import IdentityObservation, IdentityRecord, Video
from app.schemas import CrossVideoProjectionResponse
from app.services.embedding_projection import cosine_similarity, project_prototypes

router = APIRouter(prefix="/embeddings", tags=["embeddings"])

_PROJECTION_METHODS = "^(tsne|pca|umap)$"


@router.get("/projection", response_model=CrossVideoProjectionResponse)
def get_cross_video_projection(
    method: str = Query(default="tsne", pattern=_PROJECTION_METHODS),
    max_points: int = Query(default=1000, ge=1, le=20000),
    db: Annotated[Session, Depends(get_db)] = None,
) -> dict:
    """Return 2D coordinates pooling observation embeddings across all processed videos."""
    processed_ids = db.scalars(select(Video.id).where(Video.status == "processed")).all()
    if not processed_ids:
        return {"points": [], "method": method, "total": 0, "videoCount": 0}

    rows = db.scalars(
        select(IdentityObservation)
        .where(
            IdentityObservation.video_id.in_(processed_ids),
            IdentityObservation.vector.is_not(None),
        )
        .order_by(IdentityObservation.video_id, IdentityObservation.frame_id)
    ).all()
    if not rows:
        return {
            "points": [],
            "method": method,
            "total": 0,
            "videoCount": len(processed_ids),
        }

    sampled = rows
    if len(sampled) > max_points:
        step = len(sampled) / max_points
        sampled = [sampled[int(i * step)] for i in range(max_points)]

    prototypes = {
        (row.video_id, row.identity_id): row.prototype
        for row in db.scalars(select(IdentityRecord)).all()
    }
    vectors = [r.vector for r in sampled]
    coordinates = project_prototypes(vectors, method=method)
    points = [
        {
            "x": coordinates[i][0],
            "y": coordinates[i][1],
            "videoId": row.video_id,
            "identityId": row.identity_id,
            "frameId": row.frame_id,
            "trackId": row.track_id,
            "bbox": row.bbox,
            "confidence": row.confidence,
            "isOccluded": row.is_occluded,
            "qualityScore": cosine_similarity(
                row.vector, prototypes[(row.video_id, row.identity_id)]
            )
            if (row.video_id, row.identity_id) in prototypes
            else None,
        }
        for i, row in enumerate(sampled)
    ]
    return {
        "points": points,
        "method": method,
        "total": len(points),
        "videoCount": len(processed_ids),
    }
