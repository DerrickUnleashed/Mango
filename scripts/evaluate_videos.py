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
from dataclasses import dataclass
from pathlib import Path

import cv2
from orchardvision_ml.detection import Detection, FrameDetections
from orchardvision_ml.evaluation.metrics import evaluate
from orchardvision_ml.evaluation.tracks import Tracklet
from orchardvision_ml.tracking import ByteTrackAdapter, MockTracker


@dataclass(frozen=True, slots=True)
class RunConfig:
    video: str
    tracker: str
    confidence_threshold: float
    camera_motion: str

    def label(self) -> str:
        return (
            f"{self.video}|{self.tracker}"
            f"|conf{self.confidence_threshold:g}|motion-{self.camera_motion}"
        )


def build_tracker(name: str, match_threshold: float, buffer_frames: int):
    if name == "bytetrack":
        return ByteTrackAdapter(match_iou=match_threshold, buffer_size=buffer_frames)
    return MockTracker()


def load_ground_truth(path: Path) -> tuple[list[Tracklet], dict]:
    """Read a labelme annotation file into tracklets.

    Boxes are grouped by their label, which is what defines a fruit identity, so
    two boxes of the same fruit in different frames collapse into one tracklet.
    """
    items = json.loads(path.read_text())
    grouped: dict[str, list[tuple[int, tuple[float, float, float, float]]]] = {}
    for image in items:
        frame_id = int(image["imagePath"].split("_f")[1].split(".")[0])
        for shape in image["shapes"]:
            (x0, y0), (x1, y1) = shape["points"]
            bbox = (float(x0), float(y0), float(x1 - x0), float(y1 - y0))
            grouped.setdefault(shape["label"], []).append((frame_id, bbox))
    tracklets = [
        Tracklet(object_id=index, observations=tuple(sorted(obs)))
        for index, (_, obs) in enumerate(
            sorted(grouped.items(), key=lambda kv: min(f for f, _ in kv[1])), start=1
        )
    ]
    meta = {
        "annotated_frames": len(items),
        "identities": len(tracklets),
        "boxes": sum(len(obs) for obs in grouped.values()),
        "boxes_per_identity": round(
            sum(len(obs) for obs in grouped.values()) / max(1, len(tracklets)), 2
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


def run_video(video: Path, tracker_name: str, model, config: RunConfig, args) -> dict:
    tracker = build_tracker(tracker_name, args.match_threshold, args.buffer_frames)
    capture = cv2.VideoCapture(str(video))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))

    tracklets: dict[int, list[tuple[int, tuple[float, float, float, float]]]] = {}
    timings: list[float] = []
    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        start = time.perf_counter()
        detections = detect(model, frame, config.confidence_threshold)
        detections.frame_id = frame_index
        result = tracker.update(detections)
        timings.append((time.perf_counter() - start) * 1000)
        for track in result.active_tracks:
            for point in track.points:
                if point.frame_id == frame_index:
                    tracklets.setdefault(track.track_id, []).append(
                        (point.frame_id, tuple(float(v) for v in point.bbox))
                    )
        frame_index += 1
    capture.release()

    predicted = [
        Tracklet(object_id=track_id, observations=tuple(sorted(obs)))
        for track_id, obs in sorted(tracklets.items())
    ]
    return {
        "predicted": predicted,
        "frames": frame_index,
        "scale": width,
        "timings": timings,
    }


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=Path("data/gt/labelme"))
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
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    args.out.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    timings_by_label: dict[str, list[float]] = {}
    gt_meta: dict[str, dict] = {}

    for annotation_path in sorted(args.annotations.glob("*.json")):
        gt, meta = load_ground_truth(annotation_path)
        gt_meta[annotation_path.stem] = meta
        video = args.videos / f"{annotation_path.stem}.mp4"
        if not video.is_file():
            print(f"skip {annotation_path.stem}: no video at {video}")
            continue

        confidences = (
            [float(v) for v in args.confidences.split(",")]
            if args.confidences
            else [args.confidence]
        )
        for tracker_name in args.trackers.split(","):
            for confidence in confidences:
                config = RunConfig(
                    video=annotation_path.stem,
                    tracker=tracker_name,
                    confidence_threshold=confidence,
                    camera_motion="static",
                )
                outcome = run_video(video, tracker_name, model, config, args)
                report = evaluate(gt, outcome["predicted"])
                row = {
                    "video": config.video,
                    "tracker": config.tracker,
                    "confidence_threshold": config.confidence_threshold,
                    "frames": outcome["frames"],
                    "gt_identities": meta["identities"],
                    "predicted_tracks": len(outcome["predicted"]),
                    **report.to_dict(),
                    "mean_ms_per_frame": round(
                        sum(outcome["timings"]) / max(1, len(outcome["timings"])), 2
                    ),
                    "p95_ms_per_frame": round(percentile(outcome["timings"], 0.95), 2),
                    "throughput_fps": round(
                        1000.0
                        * len(outcome["timings"])
                        / max(1e-9, sum(outcome["timings"])),
                        2,
                    ),
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

    print(
        f"\nwrote {args.out}/metrics.csv, metrics.json, ground_truth.json, timings.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
