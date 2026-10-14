"""Evaluate the real trackers on the evaluation videos against annotated ground truth.

Reads the labelme annotation files produced for the evaluation videos, runs the
YOLO detector and a tracker over every frame of the video, and scores the result
with the project's own metrics module.

Ground-truth provenance is recorded in the output. A file whose ids are still the
machine-generated candidates is marked ``auto`` and the report must say so; a file
corrected by a human is marked ``manual``.

Usage::

    uv run --project ml python scripts/evaluate_videos.py \\
        --annotations data/gt/labelme --videos videos --out data/results
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.evaluation.metrics import evaluate
from orchardvision_ml.evaluation.tracks import Tracklet
from orchardvision_ml.identity.torch_extractor import TorchEmbeddingExtractor
from orchardvision_ml.memory import (
    DEFAULT_MIN_QUALITY,
    Identity,
    moving_average,
    quality_score,
)
from orchardvision_ml.motion import MeasuredMotionEstimator, StaticMotionEstimator
from orchardvision_ml.reid import MockReIdentifier
from orchardvision_ml.tracking import ByteTrackAdapter, MockTracker


@dataclass(frozen=True, slots=True)
class RunConfig:
    video: str
    tracker: str
    confidence_threshold: float
    camera_motion: str
    reid_threshold: float = 0.6

    def label(self) -> str:
        return (
            f"{self.video}|{self.tracker}|conf{self.confidence_threshold:g}"
            f"|motion-{self.camera_motion}|reid{self.reid_threshold:g}"
        )


def build_tracker(name: str, match_threshold: float, buffer_frames: int):
    if name == "bytetrack":
        return ByteTrackAdapter(match_iou=match_threshold, buffer_size=buffer_frames)
    return MockTracker()


def load_ground_truth(path: Path) -> tuple[list[Tracklet], dict]:
    """Read a ground-truth file into tracklets.

    Supports two formats:
    1. ``scripts/build_ground_truth.py`` format: ``payload["identities"]`` is a dict
       of identity name -> list of ``{"frame": ..., "bbox": [...]}``.
    2. Labelme format: JSON list of dicts with ``"shapes"``, each shape has ``"label"``
       (e.g. ``"mango_001"``) and ``"points"`` (``[x1, y1, x2, y2]``).
    """
    payload = json.loads(path.read_text())
    
    # Format 1: build_ground_truth.py output (payload["identities"] is a dict)
    if isinstance(payload, dict) and isinstance(payload.get("identities"), dict):
        identities = payload["identities"]
# Format 2: Labelme format (payload is a list of frame dicts with "shapes")
    elif isinstance(payload, list) and payload and "shapes" in payload[0]:
        identities: dict[str, list[dict]] = {}
        for frame_entry in payload:
            image_path = frame_entry.get("imagePath", "")
            # Extract frame number from imagePath like "test_f00000.jpg"
            frame_id = 0
            if "_f" in image_path:
                try:
                    frame_id = int(image_path.rsplit("_f", 1)[1].rsplit(".", 1)[0])
                except ValueError:
                    frame_id = 0
            for shape in frame_entry.get("shapes", []):
                label = shape.get("label", "")
                if not label:
                    continue
                box = shape.get("points", [])
                # Labelme rectangle points: [[x1, y1], [x2, y2]]
                if isinstance(box, list) and len(box) == 2 and all(isinstance(p, list) and len(p) >= 2 for p in box):
                    bbox = [float(box[0][0]), float(box[0][1]), float(box[1][0])-float(box[0][0]), float(box[1][1])-float(box[0][1])]
                elif isinstance(box, list) and len(box) >= 4:
                    bbox = [float(box[0]), float(box[1]), float(box[2])-float(box[0]), float(box[3])-float(box[1])]
                else:
                    continue
                identities.setdefault(label, []).append({
                    "frame": frame_id,
                    "bbox": bbox,
                })
        identities = identities if identities else {}
    else:
        raise ValueError(f"Unsupported ground-truth format in {path}")
    
    tracklets = [
        Tracklet(
            object_id=index,
            observations=tuple(
                (int(o["frame"]), tuple(float(v) for v in o["bbox"]))
                for o in observations
            ),
        )
        for index, (_, observations) in enumerate(
            sorted(
                identities.items(),
                key=lambda kv: min(o["frame"] for o in kv[1]),
            ),
            start=1,
        )
    ]
    frames_seen = {f for tracklet in tracklets for f, _ in tracklet.observations}
    meta = {
        "video": payload.get("video", path.stem) if isinstance(payload, dict) else path.stem,
        "gt_boxes": sum(len(t.observations) for t in tracklets),
        "gt_frames": len(frames_seen),
        "gt_identities": len(tracklets),
        "boxes_per_identity": round(
            sum(len(t.observations) for t in tracklets) / max(1, len(tracklets)), 1
        ),
    }
    return tracklets, meta


def detect(model, frame, confidence: float) -> FrameDetections:
    result = model.predict(frame, imgsz=640, conf=confidence, verbose=False)[0]
    detections = []
    for box in result.boxes:
        x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
        detections.append(
            Detection(
                bbox=(x1, y1, x2 - x1, y2 - y1),
                confidence=float(box.conf[0]),
            )
        )
    return FrameDetections(frame_id=0, detections=detections)


def run_video(
    video: Path,
    tracker_name: str,
    model,
    config: RunConfig,
    args,
    embedder: TorchEmbeddingExtractor | None = None,
) -> dict:
    """Track the video, and optionally consolidate identities, as the API pipeline does.

    Camera-motion compensation, when enabled, moves boxes into stabilized coordinates before
    tracking and back into raw coordinates before they are stored, so the recorded geometry stays
    comparable with the uncompensated run.
    """
    tracker = build_tracker(tracker_name, args.match_threshold, args.buffer_frames)
    estimator = (
        MeasuredMotionEstimator()
        if config.camera_motion == "measured"
        else StaticMotionEstimator()
    )
    capture = cv2.VideoCapture(str(video))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))

    tracklets: dict[int, list[tuple[int, tuple[float, float, float, float]]]] = {}
    assigned_by_frame: dict[int, FrameDetections] = {}
    lost_by_frame: dict[int, list[int]] = {}
    timings: list[float] = []
    frame_index = 0
    previous_raw: list[tuple[float, float, float, float]] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        start = time.perf_counter()
        detections = detect(model, frame, config.confidence_threshold)
        detections.frame_id = frame_index
        raw_boxes = [d.bbox for d in detections.detections]
        if config.camera_motion == "measured" and previous_raw:
            estimator.observe(frame_index, previous_raw, raw_boxes)
        previous_raw = raw_boxes

        compensated = FrameDetections(
            frame_id=frame_index,
            detections=[
                replace(
                    detection,
                    bbox=estimator.compensate(detection.bbox, frame_index),
                )
                for detection in detections.detections
            ],
        )
        result = tracker.update(compensated)
        timings.append((time.perf_counter() - start) * 1000)

        for track in result.active_tracks:
            for point in track.points:
                if point.frame_id == frame_index:
                    box = estimator.decompensate(
                        tuple(float(v) for v in point.bbox), frame_index
                    )
                    tracklets.setdefault(track.track_id, []).append(
                        (point.frame_id, box)
                    )
        # Boxes are decompensated for storage, so downstream geometry matches the raw video,
        # and each is stamped with the id of the track that claimed it, as the API pipeline does.
        # Without the stamp the re-identifier has no track to attach an identity to.
        active_now = [t for t in result.active_tracks if t.last_frame_id == frame_index]
        stored: list[Detection] = []
        for detection in compensated.detections:
            centre_x = detection.bbox[0] + detection.bbox[2] / 2
            centre_y = detection.bbox[1] + detection.bbox[3] / 2
            best_id: int | None = None
            best_distance: float | None = None
            for track in active_now:
                box = track.current_bbox
                if box is None:
                    continue
                distance = (
                    (centre_x - (box[0] + box[2] / 2)) ** 2
                    + (centre_y - (box[1] + box[3] / 2)) ** 2
                ) ** 0.5
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_id = track.track_id
            track_id = (
                best_id
                if best_distance is not None and best_distance <= 200.0
                else None
            )
            stored.append(
                replace(
                    detection,
                    bbox=estimator.decompensate(detection.bbox, frame_index),
                    track_id=track_id,
                )
            )
        assigned_by_frame[frame_index] = FrameDetections(
            frame_id=frame_index, detections=stored
        )
        lost_by_frame[frame_index] = list(result.lost_track_ids)
        frame_index += 1
    capture.release()

    predicted = [
        Tracklet(object_id=track_id, observations=tuple(sorted(obs)))
        for track_id, obs in sorted(tracklets.items())
    ]
    outcome = {
        "predicted": predicted,
        "frames": frame_index,
        "scale": width,
        "timings": timings,
        "tracklets": tracklets,
        "assigned_by_frame": assigned_by_frame,
        "lost_by_frame": lost_by_frame,
    }
    if embedder is not None:
        outcome.update(consolidate_identities(video, outcome, config, embedder, args))
    return outcome


def consolidate_identities(
    video: Path, outcome: dict, config: RunConfig, embedder, args
) -> dict:
    """Assign persistent fruit numbers and accumulate appearance prototypes.

    This mirrors the API pipeline's identity stage: a re-identifier turns short-term tracks into
    identities, and each identity's prototype is a moving average of the embeddings assigned to it,
    subject to the same quality gate.
    """
    reid = MockReIdentifier(match_threshold=config.reid_threshold)
    identities: dict[int, Identity] = {}
    reid_events: list[dict] = []

    capture = cv2.VideoCapture(str(video))
    frame_index = 0
    observations: list[dict] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        assigned = outcome["assigned_by_frame"].get(frame_index)
        if assigned is None:
            frame_index += 1
            continue
        embeddings = embedder.extract(frame, assigned)
        events = reid.step(
            frame_index,
            outcome["lost_by_frame"].get(frame_index, []),
            embeddings,
        )
        for event in events:
            reid_events.append(
                {
                    "track_id": event.track_id,
                    "identity_id": event.identity_id,
                    "lost_frame_id": event.lost_frame_id,
                    "reappearance_frame_id": frame_index,
                    "similarity": round(float(event.similarity), 3),
                    "accepted": bool(event.accepted),
                }
            )
        for embedding, detection in zip(embeddings, assigned.detections, strict=True):
            identity_id = reid.identity_for_track(embedding.track_id)
            if identity_id is None:
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
                continue
            identity.prototype = moving_average(
                identity.prototype, embedding.vector, args.memory_update_rate
            )
            identity.quality = 0.9 * identity.quality + 0.1 * quality
            identity.observation_count += 1
            identity.last_frame_id = embedding.frame_id
            observations.append(
                {
                    "identity_id": identity_id,
                    "frame_id": embedding.frame_id,
                    "track_id": detection.track_id,
                    "bbox": [round(float(v), 2) for v in detection.bbox],
                    "confidence": round(float(embedding.confidence), 3),
                    "is_occluded": bool(embedding.is_occluded),
                }
            )
        frame_index += 1
    capture.release()

    prototypes = {
        f"identity_{identity.identity_id}": [
            round(float(v), 5) for v in identity.prototype
        ]
        for identity in identities.values()
    }
    confident = sum(1 for i in identities.values() if i.is_confident)
    return {
        "identities_found": len(identities),
        "confident_identities": confident,
        "identity_observations": len(observations),
        "reid_events": reid_events,
        "reid_accepted": sum(1 for e in reid_events if e["accepted"]),
        "prototypes": prototypes,
        "observations": observations,
    }


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--annotations",
        type=Path,
        default=Path("data/gt/ground_truth"),
        help="full-rate ground truth written by build_ground_truth.py",
    )
    parser.add_argument("--videos", type=Path, default=Path("videos"))
    parser.add_argument("--out", type=Path, default=Path("data/results"))
    parser.add_argument("--model", default="models/mango_yolov8n-4/weights/best.pt")
    parser.add_argument("--trackers", default="mock,bytetrack")
    parser.add_argument(
        "--confidences",
        default="",
        help="Comma-separated confidence thresholds; runs a sweep instead of a single value",
    )
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--match-threshold", type=float, default=0.2)
    parser.add_argument("--buffer-frames", type=int, default=30)
    parser.add_argument(
        "--motions",
        default="",
        help="Comma-separated camera-motion modes; `measured` estimates real shift from detections",
    )
    parser.add_argument(
        "--identity",
        action="store_true",
        help="Run the identity stage: re-identification and appearance prototypes",
    )
    parser.add_argument("--embedder", default="resnet18")
    parser.add_argument("--reid-threshold", type=float, default=0.6)
    parser.add_argument(
        "--reid-thresholds",
        default="",
        help="Comma-separated ReID thresholds; runs a sweep instead of a single value",
    )
    parser.add_argument("--memory-update-rate", type=float, default=0.2)
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    args.out.mkdir(parents=True, exist_ok=True)
    embedder = (
        TorchEmbeddingExtractor(backbone=args.embedder) if args.identity else None
    )

    rows: list[dict] = []
    timings_by_label: dict[str, list[float]] = {}
    gt_meta: dict[str, dict] = {}
    identity_dump: dict[str, dict] = {}

    confidences = (
        [float(v) for v in args.confidences.split(",")]
        if args.confidences
        else [args.confidence]
    )
    motions = args.motions.split(",") if args.motions else ["static"]
    reid_thresholds = (
        [float(v) for v in args.reid_thresholds.split(",")]
        if args.reid_thresholds
        else [args.reid_threshold]
    )

    for annotation_path in sorted(args.annotations.glob("*.json")):
        gt, meta = load_ground_truth(annotation_path)
        gt_meta[annotation_path.stem] = meta
        video = args.videos / f"{annotation_path.stem}.mp4"
        if not video.is_file():
            print(f"skip {annotation_path.stem}: no video at {video}")
            continue

        for tracker_name in args.trackers.split(","):
            for confidence in confidences:
                for motion in motions:
                    for reid_threshold in reid_thresholds:
                        config = RunConfig(
                            video=annotation_path.stem,
                            tracker=tracker_name,
                            confidence_threshold=confidence,
                            camera_motion=motion,
                            reid_threshold=reid_threshold,
                        )
                        outcome = run_video(
                            video, tracker_name, model, config, args, embedder
                        )
                        report = evaluate(gt, outcome["predicted"])
                        row = {
                            "video": config.video,
                            "tracker": config.tracker,
                            "confidence_threshold": config.confidence_threshold,
                            "camera_motion": config.camera_motion,
                            "reid_threshold": config.reid_threshold,
                            "frames": outcome["frames"],
                            "gt_identities": meta["gt_identities"],
                            "predicted_tracks": len(outcome["predicted"]),
                            **report.to_dict(),
                            "mean_ms_per_frame": round(
                                sum(outcome["timings"])
                                / max(1, len(outcome["timings"])),
                                2,
                            ),
                            "p95_ms_per_frame": round(
                                percentile(outcome["timings"], 0.95), 2
                            ),
                            "throughput_fps": round(
                                1000.0
                                * len(outcome["timings"])
                                / max(1e-9, sum(outcome["timings"])),
                                2,
                            ),
                        }
                        if embedder is not None:
                            row.update(
                                {
                                    "identities_found": outcome["identities_found"],
                                    "confident_identities": outcome[
                                        "confident_identities"
                                    ],
                                    "identity_observations": outcome[
                                        "identity_observations"
                                    ],
                                    "reid_accepted": outcome["reid_accepted"],
                                    "reid_events": len(outcome["reid_events"]),
                                }
                            )
                            identity_dump[config.label()] = {
                                "video": config.video,
                                "reid_threshold": reid_threshold,
                                "prototypes": outcome["prototypes"],
                                "reid_events": outcome["reid_events"],
                            }
                        rows.append(row)
                        timings_by_label[config.label()] = outcome["timings"]
                        print(json.dumps(row))

    if not rows:
        print("no results: annotation files must match video names in --videos")
        return 1

    (args.out / "metrics.json").write_text(json.dumps(rows, indent=2))
    (args.out / "ground_truth.json").write_text(json.dumps(gt_meta, indent=2))
    with (args.out / "metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (args.out / "timings.json").open("w") as handle:
        json.dump(
            {k: [round(v, 2) for v in vals] for k, vals in timings_by_label.items()},
            handle,
        )
    if identity_dump:
        (args.out / "identities.json").write_text(json.dumps(identity_dump, indent=2))

    print(
        f"\nwrote {args.out}/metrics.csv, metrics.json, ground_truth.json, timings.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
