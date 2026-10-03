"""Real end-to-end counting pipeline.

Wires the concrete pipeline stages into a single runnable object:

    video → detector → tracker → embedder → memory → re-identifier → count

The orchestrator owns the per-frame loop, coordinates component handoffs, and
accumulates a :class:`PipelineResult` with the final mango identities.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from orchardvision_ml.camera import VideoInfo, VideoSource
from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.identity import Embedding, EmbeddingExtractor
from orchardvision_ml.memory import Identity, IdentityMemory
from orchardvision_ml.motion import MockMotionEstimator, MotionEstimator
from orchardvision_ml.reid import ReIdentifier
from orchardvision_ml.tracking import ByteTrackAdapter, Tracker

EMBED_EVERY_N_FRAMES = 10


@dataclass(slots=True)
class PipelineResult:
    """Outcome of a full-pipeline run over one video."""

    final_count: int
    identities: list[Identity]
    detection_count: int = 0
    track_count: int = 0
    reid_events: int = 0
    frames_processed: int = 0
    elapsed_seconds: float = 0.0
    per_frame_counts: list[int] = field(default_factory=list)
    video: VideoInfo | None = None


class CountingPipeline:
    """Runs the real detector→tracker→embed→memory→re-id chain per frame.

    Args:
        detector: Object detector (YOLO adapter or mock).
        tracker: Short-term tracker (ByteTrack adapter or mock).
        embedder: Appearance embedding extractor.
        memory: Identity memory.
        reidentifier: Re-identification engine tied to the memory.
        motion_estimator: Camera-motion estimator; defaults to static-camera.
        embed_every_n_frames: Embed tracks every Nth frame (appearance changes
            slowly; less frequent embedding saves compute).
    """

    def __init__(
        self,
        detector,
        tracker: Tracker | None = None,
        embedder: EmbeddingExtractor | None = None,
        memory: IdentityMemory | None = None,
        reidentifier: ReIdentifier | None = None,
        motion_estimator: MotionEstimator | None = None,
        embed_every_n_frames: int = EMBED_EVERY_N_FRAMES,
    ) -> None:
        self.detector = detector
        self.tracker = tracker or ByteTrackAdapter()
        self.embedder = embedder
        self.memory = memory
        self.reidentifier = reidentifier
        self.motion = motion_estimator or MockMotionEstimator()
        self.embed_every_n_frames = max(1, int(embed_every_n_frames))

    def run(self, video: VideoSource) -> PipelineResult:
        """Process every frame of ``video`` and return the count result."""
        started = time.perf_counter()
        identities: list[Identity] = []
        total_detections = 0
        total_tracks = 0
        reid_events = 0
        per_frame_counts: list[int] = []

        for frame_id, frame in video:
            frame_detections = self.detector.detect(frame, frame_id)
            detections = self._stabilize(frame_id, frame_detections.detections)
            total_detections += len(detections)

            if self.tracker.supports_frame_input:
                self.tracker.update_frame(frame)

            track_result = self.tracker.update(
                FrameDetections(frame_id=frame_id, detections=detections)
            )
            total_tracks = max(total_tracks, track_result.total_tracks)

            tracked_detections = self._assign_track_ids(detections, track_result)

            embeddings: list[Embedding] = []
            if self.embedder is not None and frame_id % self.embed_every_n_frames == 0:
                embeddings = self.embedder.extract(
                    frame, FrameDetections(frame_id, tracked_detections)
                )

            if self.memory is not None and self.reidentifier is not None:
                for embedding in embeddings:
                    if embedding.track_id is None:
                        continue
                    self.memory.update(embedding)
                events = self.reidentifier.step(
                    frame_id,
                    track_result.lost_track_ids,
                    embeddings,
                    self.memory,
                )
                reid_events += len(events)

            count = len(self.memory.identities) if self.memory is not None else 0
            per_frame_counts.append(count)

        if self.memory is not None:
            identities = list(self.memory.identities)

        return PipelineResult(
            final_count=len(identities),
            identities=identities,
            detection_count=total_detections,
            track_count=total_tracks,
            reid_events=reid_events,
            frames_processed=len(per_frame_counts),
            elapsed_seconds=time.perf_counter() - started,
            per_frame_counts=per_frame_counts,
            video=video.video_info,
        )

    def _stabilize(self, frame_id: int, detections: list[Detection]) -> list[Detection]:
        """Apply camera-motion compensation to detection coordinates."""
        if self.motion is None:
            return detections
        self.motion.estimate(frame_id)
        compensated: list[Detection] = []
        for det in detections:
            x, y, w, h = self.motion.compensate(det.bbox, frame_id)
            compensated.append(
                Detection(
                    bbox=(x, y, w, h),
                    confidence=det.confidence,
                    class_label=det.class_label,
                    track_id=det.track_id,
                )
            )
        return compensated

    @staticmethod
    def _assign_track_ids(detections, track_result) -> list[Detection]:
        """Stamp each detection with the short-term track id it belongs to."""
        track_centers: list[tuple[int, tuple[float, float]]] = []
        for track in track_result.active_tracks:
            bbox = track.current_bbox
            if bbox is None:
                continue
            cx = bbox[0] + bbox[2] / 2.0
            cy = bbox[1] + bbox[3] / 2.0
            track_centers.append((track.track_id, (cx, cy)))

        if not track_centers:
            return detections

        assigned: list[Detection] = []
        for det in detections:
            cx, cy = det.center
            track_id = det.track_id
            best_dist = float("inf")
            for tid, (tx, ty) in track_centers:
                dist = (cx - tx) ** 2 + (cy - ty) ** 2
                if dist < best_dist:
                    best_dist = dist
                    track_id = tid
            assigned.append(
                Detection(
                    bbox=det.bbox,
                    confidence=det.confidence,
                    class_label=det.class_label,
                    track_id=track_id,
                )
            )
        return assigned
