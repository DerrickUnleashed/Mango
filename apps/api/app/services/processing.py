"""Asynchronous video processing pipeline.

The pipeline runs in a background thread and progresses through well-defined
stages (frame extraction → detection → tracking → embedding → memory → re-ID →
analytics). Stage implementations are added incrementally; the service is
structured so real model adapters can replace Mock components later without
changing this orchestration layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import cv2
from numpy.typing import NDArray
from orchardvision_ml.detection import MockDetector
from orchardvision_ml.detection.mock import SCENARIO_ORCHARD
from orchardvision_ml.tracking import ByteTrackAdapter, MockTracker, Tracker
from sqlalchemy import delete

from app.core.logging import job_logger
from app.models import ProcessingJob, ProcessingStage, ProcessingStatus, Track, Video
from app.services.storage import storage_service

from .job_manager import JobState

DEFAULT_MAX_FRAMES = 600


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    inference_mode: str = "mock"
    confidence_threshold: float = 0.35
    tracker: str = "mock"
    max_frames: int | None = None

    def effective_max_frames(self, total_frames: int) -> int:
        cap = self.max_frames or DEFAULT_MAX_FRAMES
        return max(1, min(cap, total_frames))


@dataclass(slots=True)
class PipelineSummary:
    processed_frames: int
    total_detections: int
    average_confidence: float
    inference_mode: str
    tracker: str
    total_tracks: int
    new_tracks: int
    lost_tracks: int


class ProcessingService:
    """Orchestrates per-video analysis in a background thread."""

    def run(
        self,
        db,
        video: Video,
        job: ProcessingJob,
        state: JobState,
        config: PipelineConfig,
    ) -> PipelineSummary:
        log = job_logger("processing", job_id=job.id, video_id=video.id)

        job.inference_mode = config.inference_mode
        state.inference_mode = config.inference_mode

        try:
            frames = self.extract_frames(video, state, config)
            detections = self.detect_frames(video, job, state, config, frames)
            track_summary = self.track_frames(
                video, job, state, config, detections["frame_detections"], db
            )
            summary = self.analytics_summary(detections, track_summary, config)
            self._finalize(job, video, summary, state)
            log.info("Pipeline complete: %s", summary)
            return summary
        except Exception:
            log.exception("Processing failed for video %s", video.id)
            job.status = ProcessingStatus.FAILED
            job.stage = ProcessingStage.FAILED
            job.error = "Video processing failed"
            state.update(ProcessingStage.FAILED, 100.0, "Processing failed")
            raise

    def extract_frames(
        self, video: Video, state: JobState, config: PipelineConfig
    ) -> list[NDArray]:
        """Decode up to ``max_frames`` frames from the stored video."""
        max_frames = config.effective_max_frames(video.frame_count or 0)
        source = storage_service.resolve(video.filename)

        state.update(ProcessingStage.EXTRACTING_FRAMES, 10.0, "Extracting frames")

        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise ValueError("Could not open video file for frame extraction")

        frames: list[NDArray] = []
        try:
            index = 0
            while index < max_frames:
                if state.cancelled:
                    raise InterruptedError("Processing cancelled")
                ok, frame = cap.read()
                if not ok:
                    break
                frames.append(frame)
                index += 1
                if index % 50 == 0:
                    state.update(
                        ProcessingStage.EXTRACTING_FRAMES,
                        10.0 + 20.0 * (index / max(max_frames, 1)),
                        f"Extracting frame {index}/{max_frames}",
                    )
        finally:
            cap.release()

        if not frames:
            raise ValueError("No frames could be extracted from the video")

        log = job_logger("processing", job_id=state.job_id, video_id=video.id)
        log.info("Extracted %d frames for processing", len(frames))
        state.update(ProcessingStage.DETECTING, 30.0, f"Detecting across {len(frames)} frames")
        return frames

    def detect_frames(
        self,
        video: Video,
        job: ProcessingJob,
        state: JobState,
        config: PipelineConfig,
        frames: list[NDArray],
    ) -> dict:
        del job
        detector = MockDetector(scenario=SCENARIO_ORCHARD)
        total_detections = 0
        confidences: list[float] = []
        frame_count = len(frames)
        frame_detections: list = []

        for index, frame in enumerate(frames):
            if state.cancelled:
                raise InterruptedError("Processing cancelled")
            result = detector.detect(frame, index)
            total_detections += len(result)
            confidences.extend(d.confidence for d in result.detections)
            frame_detections.append(result)

            if index % 20 == 0:
                progress = 30.0 + 25.0 * (index + 1) / max(frame_count, 1)
                msg = f"Frame {index + 1}/{frame_count}"
                state.update(ProcessingStage.DETECTING, progress, msg)

        avg_conf = float(sum(confidences)) / len(confidences) if confidences else 0.0
        log = job_logger("processing", job_id=state.job_id, video_id=video.id)
        log.info(
            "Detection step complete: %d detections across %d frames (avg conf %.2f)",
            total_detections,
            frame_count,
            avg_conf,
        )

        return {
            "processed_frames": frame_count,
            "total_detections": total_detections,
            "average_confidence": avg_conf,
            "frame_detections": frame_detections,
        }

    def track_frames(
        self,
        video: Video,
        job: ProcessingJob,
        state: JobState,
        config: PipelineConfig,
        frame_detections: list,
        db,
    ) -> dict:
        """Associate per-frame detections into stable tracks and persist them."""
        state.update(ProcessingStage.TRACKING, 55.0, "Tracking detections")
        tracker: Tracker = self._build_tracker(config)
        frame_count = len(frame_detections)

        new_track_count = 0
        lost_track_count = 0
        last = None
        for index, frame_detection in enumerate(frame_detections):
            if state.cancelled:
                raise InterruptedError("Processing cancelled")
            last = tracker.update(frame_detection)
            new_track_count += len(last.new_track_ids)
            lost_track_count += len(last.lost_track_ids)

            if index % 20 == 0:
                progress = 55.0 + 30.0 * (index + 1) / max(frame_count, 1)
                msg = f"Tracking frame {index + 1}/{frame_count}"
                state.update(ProcessingStage.TRACKING, progress, msg)

        # Persist final track trajectories for this job (replace prior runs)
        tracks = self._persist_tracks(job, video, last, db)

        log = job_logger("processing", job_id=state.job_id, video_id=video.id)
        log.info(
            "Tracking step complete: %d tracks, %d new, %d lost",
            len(tracks),
            new_track_count,
            lost_track_count,
        )
        state.update(ProcessingStage.ANALYTICS, 90.0, "Summarizing results")
        return {
            "tracker": tracker.name,
            "total_tracks": len(tracks),
            "new_tracks": new_track_count,
            "lost_tracks": lost_track_count,
        }

    def _build_tracker(self, config: PipelineConfig) -> Tracker:
        if config.tracker == "bytetrack":
            return ByteTrackAdapter()
        return MockTracker()

    def _persist_tracks(self, job: ProcessingJob, video: Video, result, db) -> list[Track]:
        """Write final active track trajectories into the database.

        Existing tracks for this video are deleted first so a re-run replaces
        them atomically within the caller's transaction.
        """
        db.execute(delete(Track).where(Track.video_id == video.id))
        active_tracks = result.active_tracks if result is not None else []
        fixed_points: list[Track] = []
        for trk in active_tracks:
            record = Track(
                id=uuid4().hex,
                job_id=job.id,
                video_id=video.id,
                track_id=trk.track_id,
                status="active",
                points=[
                    {
                        "frameId": p.frame_id,
                        "bbox": list(p.bbox),
                        "confidence": p.confidence,
                        "isOccluded": p.is_occluded,
                    }
                    for p in trk.points
                ],
            )
            fixed_points.append(record)
        db.add_all(fixed_points)
        return fixed_points

    def analytics_summary(
        self, detection_result: dict, track_result: dict, config: PipelineConfig
    ) -> PipelineSummary:
        return PipelineSummary(
            processed_frames=detection_result["processed_frames"],
            total_detections=detection_result["total_detections"],
            average_confidence=detection_result["average_confidence"],
            inference_mode=config.inference_mode,
            tracker=track_result["tracker"],
            total_tracks=track_result["total_tracks"],
            new_tracks=track_result["new_tracks"],
            lost_tracks=track_result["lost_tracks"],
        )

    def _finalize(
        self,
        job: ProcessingJob,
        video: Video,
        summary: PipelineSummary,
        state: JobState,
    ) -> None:
        job.status = ProcessingStatus.COMPLETED
        job.stage = ProcessingStage.COMPLETED
        job.progress = 100.0
        job.error = None
        video.status = "processed"
        state.update(ProcessingStage.COMPLETED, 100.0, "Processing complete")


processing_service = ProcessingService()
