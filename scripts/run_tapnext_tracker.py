"""Offline validation run of the TAPNext++ point tracker over a video.

Bypasses the API: reads a video with OpenCV, detects fruit with YOLO (or the
synthetic mock detector), and drives :class:`TAPNextTracker` directly,
printing a compact track/point summary. This is the recommended way to
exercise the tracker before wiring it into the API.

Usage::

    python scripts/run_tapnext_tracker.py data/videos/orchard.mp4 \
        --checkpoint models/tapnextpp_ckpt.pt \
        --model-path models/yolov8n.pt \
        --max-frames 300

Requires the ``tapnext`` extra (``uv sync --project ml --extra tapnext``) and
a downloaded checkpoint (``python scripts/download_tapnext_weights.py``).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
from orchardvision_ml.detection import FrameDetections, MockDetector, YoloDetector


def _build_detector(kind: str, model_path: str | None):
    if kind == "mock":
        return MockDetector()
    if model_path is None:
        raise SystemExit("yolo detector needs --model-path (or use --detector mock)")
    return YoloDetector(model_path, conf_threshold=0.25)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("video", type=Path, help="Input video file")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("models/tapnextpp_ckpt.pt"),
        help="TAPNext++ weights (see scripts/download_tapnext_weights.py)",
    )
    parser.add_argument("--detector", choices=("yolo", "mock"), default="yolo")
    parser.add_argument("--model-path", default=None, help="YOLO weights file")
    parser.add_argument("--max-frames", type=int, default=0, help="0 = all")
    parser.add_argument("--match-threshold-px", type=float, default=120.0)
    parser.add_argument("--buffer-size", type=int, default=30)
    parser.add_argument(
        "--rebootstrap-interval",
        type=int,
        default=0,
        help="Frames between model re-seeds that grant queries to late fruits; 0 disables",
    )
    parser.add_argument("--device", default=None, help="torch device (cuda/cpu)")
    args = parser.parse_args(argv)

    if not args.video.is_file():
        print(f"video not found: {args.video}", file=sys.stderr)
        return 2
    if not args.checkpoint.is_file():
        print(
            f"checkpoint not found: {args.checkpoint} — run "
            "scripts/download_tapnext_weights.py first",
            file=sys.stderr,
        )
        return 2

    from orchardvision_ml.tracking import TAPNextTracker

    detector = _build_detector(args.detector, args.model_path)
    tracker = TAPNextTracker(
        checkpoint_path=args.checkpoint,
        device=args.device,
        match_threshold_px=args.match_threshold_px,
        buffer_size=args.buffer_size,
        rebootstrap_interval=args.rebootstrap_interval,
    )

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        print(f"could not open video: {args.video}", file=sys.stderr)
        return 2

    started = time.perf_counter()
    frame_count = 0
    detection_count = 0
    per_frame_tracks: list[int] = []
    track_lengths: dict[int, int] = {}
    lost_total = 0

    while True:
        ok, frame = cap.read()
        if not ok or not frame.size:
            break
        if args.max_frames and frame_count >= args.max_frames:
            break

        detections = detector.detect(frame, frame_count)
        detection_count += len(detections.detections)
        tracker.update_frame(frame)
        result = tracker.update(
            FrameDetections(frame_id=frame_count, detections=detections.detections)
        )
        per_frame_tracks.append(result.total_tracks)
        for track in result.active_tracks:
            track_lengths[track.track_id] = track.length
        lost_total += len(result.lost_track_ids)
        frame_count += 1

    cap.release()
    elapsed = time.perf_counter() - started

    summary = {
        "video": str(args.video),
        "frames": frame_count,
        "detections": detection_count,
        "tracks_seen": len(track_lengths),
        "max_active_tracks": max(per_frame_tracks, default=0),
        "mean_track_length": round(sum(track_lengths.values()) / len(track_lengths), 2)
        if track_lengths
        else None,
        "longest_track": max(track_lengths.values(), default=0),
        "lost_reports": lost_total,
        "elapsed_secs": round(elapsed, 2),
        "fps": round(frame_count / elapsed, 2) if elapsed else None,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
