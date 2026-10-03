"""Asynchronous video processing pipeline.

The pipeline runs in a background thread and progresses through well-defined
stages (frame extraction → detection → tracking → embedding → memory → re-ID →
analytics). Stage implementations are added incrementally; the service is
structured so real model adapters can replace Mock components later without
changing this orchestration layer.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import cv2
from orchardvision_ml.detection import MockDetector
from orchardvision_ml.detection.mock import SCENARIO_ORCHARD
from orchardvision_ml.identity import MockEmbeddingExtractor
from orchardvision_ml.memory import DEFAULT_MIN_QUALITY, Identity, moving_average, quality_score
from orchardvision_ml.motion import MockMotionEstimator, MotionEstimator, StaticMotionEstimator
from orchardvision_ml.reid import MockReIdentifier
from orchardvision_ml.tracking import ByteTrackAdapter, MockTracker, Tracker
from sqlalchemy import delete

from app.core.config import settings
from app.core.logging import job_logger
from app.models import (
    CameraMotionRecord,
    DetectionRecord,
    FrameTimingRecord,
    IdentityObservation,
    IdentityRecord,
    ProcessingJob,
    ProcessingStage,
    ProcessingStatus,
    ReidEvent,
    Track,
    Video,
)
from app.services.job_state import ProgressState
from app.services.storage import storage_service

DEFAULT_MAX_FRAMES = 600
MAX_TRACK_ASSIGN_DISTANCE_PX = 60.0

DEFAULT_MODEL_PATH = Path(settings.yolo_weights_path)


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    inference_mode: str = "mock"
    confidence_threshold: float = 0.35
    tracker: str = "mock"
    camera_motion: str = "static"
    reid_threshold: float = 0.6
    memory_update_rate: float = 0.2
    tracker_match_threshold: float = 120.0
    tracker_buffer_frames: int = 30
    max_frames: int | None = None
    model_path: str | None = None
    sliced: int = 0
    embedding_model_path: str | None = os.environ.get("EMBEDDING_MODEL_PATH")
    tapnext_checkpoint_path: str | None = None

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
        state: ProgressState,
        config: PipelineConfig,
    ) -> PipelineSummary:
        log = job_logger("processing", job_id=job.id, video_id=video.id)

        job.inference_mode = config.inference_mode
        job.started_at = datetime.now(UTC)
        state.inference_mode = config.inference_mode

        try:
            detections = self.detect_frames(video, job, state, config)
            track_summary = self.track_frames(
                video, job, state, config, detections["frame_detections"], db
            )
            self.persist_detections(video, track_summary["assigned_detections"], db)
            self.persist_frame_timings(video, detections["frame_timings"], db)
            self.persist_motion_estimate(video, config, detections["processed_frames"], db)
            identity_summary = self.learn_identities(
                video,
                job,
                state,
                config,
                detections["processed_frames"],
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

    def detect_frames(
        self,
        video: Video,
        job: ProcessingJob,
        state: ProgressState,
        config: PipelineConfig,
    ) -> dict:
        """Extract and detect frames in a single streaming pass.

        Frames are decoded one at a time, passed to the detector, and released
        before the next is read, so peak memory stays flat regardless of video
        length (a previous design held every decoded frame in RAM for the whole
        pipeline and was OOM-killed on long videos).
        """
        del job
        detector = self._build_detector(config)
        max_frames = config.effective_max_frames(video.frame_count or 0)
        source = storage_service.resolve(video.filename)

        state.update(ProcessingStage.EXTRACTING_FRAMES, 10.0, "Extracting frames")

        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise ValueError("Could not open video file for frame extraction")

        total_detections = 0
        confidences: list[float] = []
        frame_detections: list = []
        frame_timings: list[dict] = []
        try:
            index = 0
            while index < max_frames:
                if state.cancelled:
                    raise InterruptedError("Processing cancelled")
                ok, frame = cap.read()
                if not ok:
                    break
                start = time.perf_counter()
                result = detector.detect(frame, index)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                total_detections += len(result)
                confidences.extend(d.confidence for d in result.detections)
                frame_detections.append(result)
                frame_timings.append({"frame_id": index, "elapsed_ms": elapsed_ms})
                index += 1
                if index % 20 == 0:
                    progress = 30.0 + 30.0 * (index / max(max_frames, 1))
                    msg = f"Frame {index}/{max_frames}"
                    state.update(ProcessingStage.DETECTING, progress, msg)
        finally:
            cap.release()

        frame_count = len(frame_detections)
        if frame_count == 0:
            raise ValueError("No frames could be extracted from the video")

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
            "frame_timings": frame_timings,
        }

    def _build_detector(self, config: PipelineConfig):
        """Pick a detector from the pipeline config.

        ``inference_mode="real"`` loads the trained YOLO weights (via
        :class:`orchardvision_ml.detection.YoloDetector`); mock mode returns the
        deterministic scenario detector.
        """
        if config.inference_mode == "real":
            from orchardvision_ml.detection import YoloDetector

            model_path = config.model_path or str(DEFAULT_MODEL_PATH)
            return YoloDetector(
                model_path,
                conf_threshold=config.confidence_threshold,
                sliced=config.sliced,
            )
        return MockDetector(scenario=SCENARIO_ORCHARD)

    def _build_embedder(self, config: PipelineConfig):
        """Pick an appearance embedder from the pipeline config.

        Real mode prefers a self-supervised identity checkpoint (via
        :class:`orchardvision_ml.identity.Embedder`) when the embedding model
        path is set and exists, falling back to the pretrained torchvision
        backbone. Mock mode uses the deterministic crop-feature embedder.
        """
        if config.inference_mode == "real":
            from orchardvision_ml.identity import Embedder, TorchEmbeddingExtractor

            if config.embedding_model_path:
                checkpoint = Path(config.embedding_model_path)
                if checkpoint.is_file():
                    return Embedder(checkpoint)
            return TorchEmbeddingExtractor()
        return MockEmbeddingExtractor()

    def track_frames(
        self,
        video: Video,
        job: ProcessingJob,
        state: ProgressState,
        config: PipelineConfig,
        frame_detections: list,
        db,
    ) -> dict:
        """Associate per-frame detections into stable tracks and persist them."""
        state.update(ProcessingStage.TRACKING, 60.0, "Tracking detections")
        tracker: Tracker = self._build_tracker(config)
        frame_aware = tracker.supports_frame_input
        frame_source = storage_service.resolve(video.filename) if frame_aware else None
        cap = cv2.VideoCapture(str(frame_source)) if frame_source is not None else None
        if cap is not None and not cap.isOpened():
            raise ValueError("Could not open video file for frame-aware tracking")
        motion: MotionEstimator = self._build_motion_estimator(config)
        frame_count = len(frame_detections)

        new_track_count = 0
        lost_track_count = 0
        last = None
        assigned_detections: list = []
        lost_by_frame: list = []
        try:
            for index, frame_detection in enumerate(frame_detections):
                if state.cancelled:
                    raise InterruptedError("Processing cancelled")
                if cap is not None:
                    ok, frame = cap.read()
                    if not ok:
                        raise ValueError("Video ended before tracked frames were exhausted")
                    tracker.update_frame(frame)
                stable_detection = self.compensate_frame_detections(frame_detection, motion, index)
                last = tracker.update(stable_detection)
                new_track_count += len(last.new_track_ids)
                lost_track_count += len(last.lost_track_ids)
                assigned = self._assign_track_ids(index, stable_detection, last.active_tracks)
                assigned_detections.append(
                    self._decompensate_frame_detections(assigned, motion, index)
                )
                lost_by_frame.append(list(last.lost_track_ids))

                if index % 20 == 0:
                    progress = 60.0 + 20.0 * (index + 1) / max(frame_count, 1)
                    msg = f"Tracking frame {index + 1}/{frame_count}"
                    state.update(ProcessingStage.TRACKING, progress, msg)
        finally:
            if cap is not None:
                cap.release()

        # Persist final track trajectories for this video (replace prior runs)
        tracks = self._persist_tracks(job, video, last, db, motion)

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

    def _decompensate_frame_detections(self, frame_detection, motion, frame_id):
        """Shift detection bboxes back into raw (un-stabilized) video space.

        Compensation is only an internal tracking concern; anything persisted
        (detections, embeddings, observations) must be in raw coordinates so
        overlays line up with the un-stabilized source video.
        """
        detections = frame_detection.detections
        if motion.name == "static" or not detections:
            return frame_detection
        decompensated = [
            replace(det, bbox=tuple(motion.decompensate(tuple(det.bbox), frame_id)))
            for det in detections
        ]
        return replace(frame_detection, detections=decompensated)

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
        if config.tracker == "tapnext":
            from orchardvision_ml.tracking import TAPNextTracker

            checkpoint = config.tapnext_checkpoint_path or str(settings.tapnext_checkpoint_path)
            return TAPNextTracker(
                checkpoint_path=checkpoint,
                match_threshold_px=config.tracker_match_threshold,
                buffer_size=config.tracker_buffer_frames,
            )
        return MockTracker(
            match_threshold=config.tracker_match_threshold,
            max_buffer=config.tracker_buffer_frames,
        )

    def _persist_tracks(self, job: ProcessingJob, video: Video, result, db, motion) -> list[Track]:
        """Write final active track trajectories into the database.

        Existing tracks for this video are deleted first so a re-run replaces
        them atomically within the caller's transaction. Track points are
        stored in raw video coordinates (compensation is inverted).
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
                        "bbox": list(motion.decompensate(p.bbox, p.frame_id)),
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
        state: ProgressState,
        config: PipelineConfig,
        frames: int,
        assigned_detections: list,
        lost_by_frame: list,
        db,
    ) -> dict:
        """Assign track-chain identities and consolidate their appearance profiles.

        Each short-term track belongs to exactly one identity: brand-new tracks
        get a new mango number, reappearances of a lost track keep the original
        number (via the re-identifier). Appearance embeddings are accumulated
        against those numbers for the prototype record — never used to cluster
        simultaneously-visible boxes together. Frames are re-read one at a time
        so only a single decoded frame is resident during embedding.
        """
        del job
        state.update(ProcessingStage.EMBEDDING, 80.0, "Extracting appearance embeddings")
        embedder = self._build_embedder(config)
        reid = MockReIdentifier(match_threshold=config.reid_threshold)

        source = storage_service.resolve(video.filename)
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise ValueError("Could not open video file for embedding extraction")

        frame_count = frames
        total_embeddings = 0
        suppressed = 0
        observations: list = []
        identities: dict[int, Identity] = {}
        try:
            index = 0
            while index < frame_count:
                if state.cancelled:
                    raise InterruptedError("Processing cancelled")
                ok, frame = cap.read()
                if not ok:
                    break
                assigned = assigned_detections[index]
                embeddings = embedder.extract(frame, assigned)
                total_embeddings += len(embeddings)
                reid.step(index, lost_by_frame[index], embeddings)
                for embedding, det in zip(embeddings, assigned.detections, strict=True):
                    identity_id = reid.identity_for_track(embedding.track_id)
                    if identity_id is None:
                        suppressed += 1
                        continue
                    identity = identities.get(identity_id)
                    if identity is None:
                        identity = Identity(
                            identity_id=identity_id,
                            prototype=embedding.vector.astype("float32"),
                            quality=0.0,
                            observation_count=0,
                            first_frame_id=embedding.frame_id,
                            last_frame_id=embedding.frame_id,
                            last_track_id=embedding.track_id,
                        )
                        identities[identity_id] = identity
                    quality = quality_score(embedding.confidence, embedding.is_occluded)
                    if quality < DEFAULT_MIN_QUALITY:
                        suppressed += 1
                        continue
                    identity.prototype = moving_average(
                        identity.prototype, embedding.vector, config.memory_update_rate
                    )
                    identity.quality = 0.9 * identity.quality + 0.1 * quality
                    identity.observation_count += 1
                    identity.last_frame_id = embedding.frame_id
                    identity.last_track_id = embedding.track_id
                    observations.append(
                        {
                            "identity_id": identity.identity_id,
                            "frame_id": embedding.frame_id,
                            "track_id": det.track_id,
                            "bbox": list(det.bbox),
                            "confidence": embedding.confidence,
                            "is_occluded": embedding.is_occluded,
                            "quality_after": identity.quality,
                        }
                    )
                index += 1
                if index % 20 == 0:
                    progress = 80.0 + 5.0 * (index + 1) / max(frame_count, 1)
                    msg = f"Embedding frame {index + 1}/{frame_count}"
                    state.update(ProcessingStage.EMBEDDING, progress, msg)
        finally:
            cap.release()

        records = self._persist_identities(video, identities, db)
        self._persist_identity_observations(video, observations, db)
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

    def _persist_identities(
        self, video: Video, identities: dict[int, Identity], db
    ) -> list[IdentityRecord]:
        db.execute(delete(IdentityRecord).where(IdentityRecord.video_id == video.id))
        records: list[IdentityRecord] = []
        for identity_id in sorted(identities):
            identity = identities[identity_id]
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

    def persist_frame_timings(
        self, video: Video, timings: list[dict], db
    ) -> list[FrameTimingRecord]:
        """Replace stored per-frame timing telemetry for a video run."""
        db.execute(delete(FrameTimingRecord).where(FrameTimingRecord.video_id == video.id))
        records = [
            FrameTimingRecord(
                id=uuid4().hex,
                video_id=video.id,
                frame_id=t["frame_id"],
                elapsed_ms=t["elapsed_ms"],
            )
            for t in timings
        ]
        db.add_all(records)
        return records

    def _persist_identity_observations(
        self, video: Video, observations: list[dict], db
    ) -> list[IdentityObservation]:
        db.execute(delete(IdentityObservation).where(IdentityObservation.video_id == video.id))
        records = [
            IdentityObservation(
                id=uuid4().hex,
                video_id=video.id,
                identity_id=obs["identity_id"],
                frame_id=obs["frame_id"],
                track_id=obs["track_id"],
                bbox=obs["bbox"],
                confidence=obs["confidence"],
                is_occluded=obs["is_occluded"],
                quality_after=obs["quality_after"],
            )
            for obs in observations
        ]
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
                    candidates=list(event.candidate_identity_ids),
                    candidate_scores={
                        str(candidate_id): float(score)
                        for candidate_id, score in event.candidate_scores
                    },
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
        state: ProgressState,
    ) -> None:
        job.status = ProcessingStatus.COMPLETED
        job.stage = ProcessingStage.COMPLETED
        job.progress = 100.0
        job.error = None
        job.completed_at = datetime.now(UTC)
        video.status = "processed"
        state.update(ProcessingStage.COMPLETED, 100.0, "Processing complete")


processing_service = ProcessingService()
