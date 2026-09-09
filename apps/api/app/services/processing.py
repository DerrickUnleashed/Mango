"""Asynchronous video processing pipeline.

The pipeline runs in a background thread and progresses through well-defined
stages (frame extraction → detection → tracking → embedding → memory → re-ID →
analytics). Stage implementations are added incrementally; the service is
structured so real model adapters can replace Mock components later without
changing this orchestration layer.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import uuid4

import cv2
from numpy.typing import NDArray
from orchardvision_ml.detection import MockDetector
from orchardvision_ml.detection.mock import SCENARIO_ORCHARD
from orchardvision_ml.identity import MockEmbeddingExtractor
from orchardvision_ml.memory import MockIdentityMemory
from orchardvision_ml.motion import MockMotionEstimator, MotionEstimator, StaticMotionEstimator
from orchardvision_ml.reid import MockReIdentifier
from orchardvision_ml.tracking import ByteTrackAdapter, MockTracker, Tracker
from sqlalchemy import delete

from app.core.logging import job_logger
from app.models import (
    CameraMotionRecord,
    DetectionRecord,
    IdentityRecord,
    ProcessingJob,
    ProcessingStage,
    ProcessingStatus,
    ReidEvent,
    Track,
    Video,
)
from app.services.storage import storage_service

from .job_manager import JobState

DEFAULT_MAX_FRAMES = 600
MAX_TRACK_ASSIGN_DISTANCE_PX = 60.0


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    inference_mode: str = "mock"
    confidence_threshold: float = 0.35
    tracker: str = "mock"
    camera_motion: str = "static"
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
    camera_motion: str
    total_tracks: int
    new_tracks: int
    lost_tracks: int
    total_embeddings: int
    total_identities: int
    suppressed_observations: int
    total_reidentifications: int


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
            self.persist_detections(video, track_summary["assigned_detections"], db)
            self.persist_motion_estimate(video, config, detections["processed_frames"], db)
            identity_summary = self.learn_identities(
                video,
                job,
                state,
                frames,
                track_summary["assigned_detections"],
                track_summary["lost_by_frame"],
                db,
            )
            state.update(ProcessingStage.ANALYTICS, 90.0, "Summarizing results")
            summary = self.analytics_summary(detections, track_summary, identity_summary, config)
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
        motion: MotionEstimator = self._build_motion_estimator(config)
        frame_count = len(frame_detections)

        new_track_count = 0
        lost_track_count = 0
        last = None
        assigned_detections: list = []
        lost_by_frame: list = []
        for index, frame_detection in enumerate(frame_detections):
            if state.cancelled:
                raise InterruptedError("Processing cancelled")
            stable_detection = self.compensate_frame_detections(frame_detection, motion, index)
            last = tracker.update(stable_detection)
            new_track_count += len(last.new_track_ids)
            lost_track_count += len(last.lost_track_ids)
            assigned_detections.append(
                self._assign_track_ids(index, stable_detection, last.active_tracks)
            )
            lost_by_frame.append(list(last.lost_track_ids))

            if index % 20 == 0:
                progress = 55.0 + 25.0 * (index + 1) / max(frame_count, 1)
                msg = f"Tracking frame {index + 1}/{frame_count}"
                state.update(ProcessingStage.TRACKING, progress, msg)

        # Persist final track trajectories for this video (replace prior runs)
        tracks = self._persist_tracks(job, video, last, db)

        log = job_logger("processing", job_id=state.job_id, video_id=video.id)
        log.info(
            "Tracking step complete: %d tracks, %d new, %d lost (motion=%s)",
            len(tracks),
            new_track_count,
            lost_track_count,
            motion.name,
        )
        return {
            "tracker": tracker.name,
            "camera_motion": motion.name,
            "total_tracks": len(tracks),
            "new_tracks": new_track_count,
            "lost_tracks": lost_track_count,
            "assigned_detections": assigned_detections,
            "lost_by_frame": lost_by_frame,
        }

    def _build_motion_estimator(self, config: PipelineConfig) -> MotionEstimator:
        """Pick a motion estimator from pipeline config.

        ``camera_motion="drift"`` simulates a slightly drifting camera so the
        compensation path stays exercised; real adapters will attach later.
        """
        if config.camera_motion == "drift":
            return MockMotionEstimator(dx_per_frame=0.5, dy_per_frame=0.2)
        return StaticMotionEstimator()

    def compensate_frame_detections(self, frame_detection, motion, frame_id):
        """Shift detection bboxes into motion-stabilized coordinates.

        Identity-preserving: static estimators return the detections unchanged.
        """
        detections = frame_detection.detections
        if motion.name == "static" or not detections:
            return frame_detection
        compensated = [
            replace(det, bbox=tuple(motion.compensate(tuple(det.bbox), frame_id)))
            for det in detections
        ]
        return replace(frame_detection, detections=compensated)

    def persist_motion_estimate(
        self, video: Video, config: PipelineConfig, frame_count: int, db
    ) -> CameraMotionRecord:
        """Store the run's camera-motion estimate for this video."""
        motion: MotionEstimator = self._build_motion_estimator(config)
        estimate = motion.estimate(max(frame_count - 1, 0))
        compensation_applied = not estimate.is_static
        mean_abs_shift = (estimate.dx**2 + estimate.dy**2) ** 0.5

        db.execute(delete(CameraMotionRecord).where(CameraMotionRecord.video_id == video.id))
        record = CameraMotionRecord(
            id=uuid4().hex,
            video_id=video.id,
            source=estimate.source,
            dx_per_frame=estimate.dx,
            dy_per_frame=estimate.dy,
            mean_abs_shift=mean_abs_shift,
            frames_analyzed=frame_count,
            confidence=estimate.confidence,
            compensation_applied=compensation_applied,
        )
        db.add(record)
        return record

    def _assign_track_ids(self, frame_id: int, frame_detections, active_tracks: list):
        """Stamp each detection with the id of its best-matching recent track.

        Detection objects are frozen, so replacements carry the track id.
        """
        assigned: list = []
        for det in frame_detections.detections:
            best_id: int | None = None
            best_distance: float | None = None
            det_cx, det_cy = det.center
            for track in active_tracks:
                if track.last_frame_id != frame_id:
                    continue
                bbox = track.current_bbox
                if bbox is None:
                    continue
                bx, by, bw, bh = bbox
                distance = (
                    (det_cx - (bx + bw / 2.0)) ** 2 + (det_cy - (by + bh / 2.0)) ** 2
                ) ** 0.5
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_id = track.track_id
            track_id = (
                best_id
                if best_distance is not None and best_distance <= MAX_TRACK_ASSIGN_DISTANCE_PX
                else None
            )
            assigned.append(replace(det, track_id=track_id))
        return replace(frame_detections, detections=assigned)

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

    def persist_detections(self, video: Video, assigned_detections: list, db) -> int:
        """Persist per-frame detections with their assigned track ids."""
        db.execute(delete(DetectionRecord).where(DetectionRecord.video_id == video.id))
        rows: list[DetectionRecord] = []
        for assigned in assigned_detections:
            frame_id = assigned.frame_id
            for det in assigned.detections:
                rows.append(
                    DetectionRecord(
                        id=uuid4().hex,
                        video_id=video.id,
                        frame_id=frame_id,
                        track_id=det.track_id,
                        bbox=list(det.bbox),
                        confidence=det.confidence,
                        class_label=det.class_label,
                        is_occluded=det.confidence < self._occlusion_confidence_bound(),
                    )
                )
        db.add_all(rows)
        return len(rows)

    def _occlusion_confidence_bound(self) -> float:
        return 0.45

    def learn_identities(
        self,
        video: Video,
        job: ProcessingJob,
        state: JobState,
        frames: list[NDArray],
        assigned_detections: list,
        lost_by_frame: list,
        db,
    ) -> dict:
        """Extract embeddings and consolidate them into quality-aware identities."""
        del job
        state.update(ProcessingStage.EMBEDDING, 80.0, "Extracting appearance embeddings")
        embedder = MockEmbeddingExtractor()
        memory = MockIdentityMemory()
        reid = MockReIdentifier()

        frame_count = len(frames)
        total_embeddings = 0
        suppressed = 0
        for index, assigned in enumerate(assigned_detections):
            if state.cancelled:
                raise InterruptedError("Processing cancelled")
            embeddings = embedder.extract(frames[index], assigned)
            total_embeddings += len(embeddings)
            reid.step(index, lost_by_frame[index], embeddings, memory)
            for embedding in embeddings:
                if memory.update(embedding) is None:
                    suppressed += 1
            if index % 20 == 0:
                progress = 80.0 + 5.0 * (index + 1) / max(frame_count, 1)
                msg = f"Embedding frame {index + 1}/{frame_count}"
                state.update(ProcessingStage.EMBEDDING, progress, msg)

        records = self._persist_identities(video, memory, db)
        reid_records = self._persist_reid_events(video, reid.events, db)

        state.update(
            ProcessingStage.MEMORY,
            85.0,
            f"Consolidated {len(records)} identities; {len(reid_records)} re-identifications",
        )
        log = job_logger("processing", job_id=state.job_id, video_id=video.id)
        log.info(
            "Identity step complete: %d embeddings, %d identities, %d suppressed, "
            "%d reidentifications",
            total_embeddings,
            len(records),
            suppressed,
            len(reid_records),
        )
        return {
            "total_embeddings": total_embeddings,
            "total_identities": len(records),
            "suppressed_observations": suppressed,
            "total_reidentifications": len(reid_records),
        }

    def _persist_identities(self, video: Video, memory, db) -> list[IdentityRecord]:
        db.execute(delete(IdentityRecord).where(IdentityRecord.video_id == video.id))
        records: list[IdentityRecord] = []
        for identity in memory.identities:
            records.append(
                IdentityRecord(
                    id=uuid4().hex,
                    video_id=video.id,
                    identity_id=identity.identity_id,
                    quality=identity.quality,
                    observation_count=identity.observation_count,
                    first_frame_id=identity.first_frame_id,
                    last_frame_id=identity.last_frame_id,
                    last_track_id=identity.last_track_id,
                    is_confident=identity.is_confident,
                    prototype=[float(v) for v in identity.prototype],
                )
            )
        db.add_all(records)
        return records

    def _persist_reid_events(self, video: Video, events, db) -> list[ReidEvent]:
        db.execute(delete(ReidEvent).where(ReidEvent.video_id == video.id))
        records: list[ReidEvent] = []
        for event in events:
            records.append(
                ReidEvent(
                    id=uuid4().hex,
                    video_id=video.id,
                    track_id=event.track_id,
                    victim_track_id=event.victim_track_id,
                    identity_id=event.identity_id,
                    lost_frame_id=event.lost_frame_id,
                    reappearance_frame_id=event.reappearance_frame_id,
                    similarity=event.similarity,
                    confidence=event.confidence,
                    accepted=event.accepted,
                )
            )
        db.add_all(records)
        return records

    def analytics_summary(
        self,
        detection_result: dict,
        track_result: dict,
        identity_result: dict,
        config: PipelineConfig,
    ) -> PipelineSummary:
        return PipelineSummary(
            processed_frames=detection_result["processed_frames"],
            total_detections=detection_result["total_detections"],
            average_confidence=detection_result["average_confidence"],
            inference_mode=config.inference_mode,
            tracker=track_result["tracker"],
            camera_motion=track_result["camera_motion"],
            total_tracks=track_result["total_tracks"],
            new_tracks=track_result["new_tracks"],
            lost_tracks=track_result["lost_tracks"],
            total_embeddings=identity_result["total_embeddings"],
            total_identities=identity_result["total_identities"],
            suppressed_observations=identity_result["suppressed_observations"],
            total_reidentifications=identity_result["total_reidentifications"],
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
