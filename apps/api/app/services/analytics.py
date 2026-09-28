"""Video analytics aggregations over persisted pipeline results."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import (
    CameraMotionRecord,
    DetectionRecord,
    IdentityRecord,
    ProcessingJob,
    ProcessingStatus,
    ReidEvent,
    Track,
    Video,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

CONFIDENCE_EDGES = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# The bin labels, derived from the edges so they cannot drift from
# _confidence_bin. These were previously the raw edge floats, which never
# matched the string keys _confidence_bin produces, so every count came back
# as the defaultdict zero and the confidence histogram was always empty.
CONFIDENCE_LABELS = [
    f"{CONFIDENCE_EDGES[i]:.1f}–{CONFIDENCE_EDGES[i + 1]:.1f}"
    for i in range(len(CONFIDENCE_EDGES) - 1)
]


def _confidence_bin(confidence: float) -> str:
    for label, low, high in zip(
        CONFIDENCE_LABELS, CONFIDENCE_EDGES, CONFIDENCE_EDGES[1:], strict=False
    ):
        if low <= confidence < high:
            return label
    return CONFIDENCE_LABELS[-1]


def _occlusion_runs(rows: list[dict]) -> list[int]:
    """Lengths of contiguous occluded observation runs per track."""
    runs: list[int] = []
    by_track: dict[int | None, list[bool]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["frame_id"]):
        by_track[row["track_id"]].append(row["is_occluded"])
    for flags in by_track.values():
        current = 0
        for occluded in flags:
            if occluded:
                current += 1
            elif current:
                runs.append(current)
                current = 0
        if current:
            runs.append(current)
    return sorted(runs)


def compute_video_analytics(db: Session, video: Video) -> dict:
    """Aggregate persisted detections/tracks/identities into a summary dict."""
    detections = db.scalars(
        select(DetectionRecord).where(DetectionRecord.video_id == video.id)
    ).all()
    tracks = db.scalars(select(Track).where(Track.video_id == video.id)).all()
    identities = db.scalars(select(IdentityRecord).where(IdentityRecord.video_id == video.id)).all()
    reid_events = db.scalars(select(ReidEvent).where(ReidEvent.video_id == video.id)).all()
    job = db.scalar(
        select(ProcessingJob)
        .where(
            ProcessingJob.video_id == video.id,
            ProcessingJob.status == ProcessingStatus.COMPLETED,
        )
        .order_by(ProcessingJob.completed_at.desc())
    )

    det_rows = [d.to_dict() for d in detections]
    total_frames = max(video.frame_count or 0, 1)

    fruit_per_frame: list[dict] = []
    tracks_per_frame: list[dict] = []
    losses_per_frame: list[dict] = []
    counts_by_frame: dict[int, int] = defaultdict(int)
    track_counts_by_frame: dict[int, set] = defaultdict(set)
    for row in det_rows:
        if row["frameId"] <= total_frames:
            counts_by_frame[row["frameId"]] += 1
            track_counts_by_frame[row["frameId"]].add(row["trackId"])
    for frame_id in range(total_frames):
        fruit_per_frame.append({"frameId": frame_id, "count": counts_by_frame[frame_id]})
        tracks_per_frame.append(
            {
                "frameId": frame_id,
                "count": len(track_counts_by_frame[frame_id]),
            }
        )
    for event in reid_events:
        losses_per_frame.append({"frameId": event.lost_frame_id, "count": 1})

    confidences = [row["confidence"] for row in det_rows]
    total_detections = len(det_rows)
    avg_confidence = sum(confidences) / total_detections if total_detections else 0.0

    bin_counts: dict[str, int] = defaultdict(int)
    for row in det_rows:
        bin_counts[_confidence_bin(row["confidence"])] += 1
    confidence_distribution = [
        {"label": label, "count": bin_counts[label]} for label in CONFIDENCE_LABELS
    ]

    occlusion_runs = _occlusion_runs(
        [
            {"frame_id": r["frameId"], "track_id": r["trackId"], "is_occluded": r["isOccluded"]}
            for r in det_rows
        ]
    )
    occlusion_duration_distribution: list[dict] = []
    max_run = max(occlusion_runs) if occlusion_runs else 0
    if max_run:
        for size in range(1, max_run + 1):
            label = f"{size} frame{'s' if size != 1 else ''}"
            occlusion_duration_distribution.append(
                {"label": label, "count": occlusion_runs.count(size)}
            )

    active_tracks = len(tracks)
    last_detected_frame = max(counts_by_frame) if counts_by_frame else 0
    lost_tracks = sum(
        1 for t in tracks if t.points and t.points[-1]["frameId"] < last_detected_frame
    )

    processing_seconds = 0.0
    if job and job.started_at and job.completed_at:
        processing_seconds = max((job.completed_at - job.started_at).total_seconds(), 0.0)
    total_frames_processed = max(1, last_detected_frame)
    avg_tracking_fps = (
        total_frames_processed / processing_seconds if processing_seconds > 0 else 0.0
    )

    motion = db.scalar(select(CameraMotionRecord).where(CameraMotionRecord.video_id == video.id))

    return {
        "videoId": video.id,
        "totalFrames": total_frames,
        "fruitPerFrame": fruit_per_frame,
        "uniqueIdentities": len(identities),
        "totalFruitDetections": total_detections,
        "totalFruitCount": total_detections,
        "activeTracks": active_tracks,
        "lostTracks": lost_tracks,
        "recoveredIdentities": len(reid_events),
        "idSwitches": 0,
        "trackFragmentation": 0,
        "occlusionEvents": sum(1 for r in det_rows if r["isOccluded"]),
        "avgConfidence": avg_confidence,
        "avgTrackingFps": avg_tracking_fps,
        "processingSeconds": processing_seconds,
        "confidenceDistribution": confidence_distribution,
        "occlusionDurationDistribution": occlusion_duration_distribution,
        "tracksPerFrame": tracks_per_frame,
        "lossesPerFrame": losses_per_frame,
        "cameraMotion": motion.to_dict() if motion else None,
    }
