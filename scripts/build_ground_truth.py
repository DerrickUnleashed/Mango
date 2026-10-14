"""Build the ground-truth annotation set from the detection pass.

Two problems have to be solved before any tracking metric means anything.

**Fragmentation.** The camera is handheld, so a naive IoU association across a ten
frame gap breaks a fruit into a new identity every time it is briefly occluded.
Association here runs at the full frame rate, where consecutive boxes overlap by
about 0.99 IoU, and only every tenth frame is exported for review.

**Transient identities.** Even at full frame rate an occlusion, or a false positive,
raises a short track that dies and is re-raised later as a new identity. On V1 that
produced 61 identities of which 44 lasted fewer than twenty frames, against nine
that lasted fifty frames or more, while at most ten fruit are ever on screen. Those
short tracks are dropped by a minimum-track-length rule, which is the standard way
of cleaning annotation noise and is the single reason the candidate identities were
four times too many.

Output is a labelme file per video, plus the statistics needed to judge whether the
result is sane before anyone trusts it.

Usage::

    uv run --project ml python scripts/build_ground_truth.py \\
        --detections data/gt/detections.json --videos videos \\
        --out data/gt/labelme
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def iou(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> float:
    ax1, ay1, ax2, ay2 = a[0], a[1], a[0] + a[2], a[1] + a[3]
    bx1, by1, bx2, by2 = b[0], b[1], b[0] + b[2], b[1] + b[3]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = ix2 - ix1, iy2 - iy1
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


Observation = tuple[int, tuple[float, float, float, float]]


def associate(
    frames: list[dict], match_threshold: float
) -> tuple[dict[int, list[Observation]], int]:
    """Greedy IoU association at full frame rate."""
    active: list[tuple[int, tuple[float, float, float, float]]] = []
    tracks: dict[int, list[Observation]] = {}
    next_id = 1
    for frame in frames:
        boxes = [d["box"] for d in frame["detections"]]
        pairs = sorted(
            (
                (iou(previous[1], box), index, box_index)
                for index, previous in enumerate(active)
                for box_index, box in enumerate(boxes)
            ),
            reverse=True,
        )
        used_tracks: set[int] = set()
        used_boxes: set[int] = set()
        assignment: dict[int, int] = {}
        for score, track_index, box_index in pairs:
            if score < match_threshold:
                break
            if track_index in used_tracks or box_index in used_boxes:
                continue
            used_tracks.add(track_index)
            used_boxes.add(box_index)
            assignment[box_index] = active[track_index][0]
        for box_index in range(len(boxes)):
            if box_index not in assignment:
                assignment[box_index] = next_id
                next_id += 1
        for box_index in range(len(boxes)):
            track_id = assignment[box_index]
            tracks.setdefault(track_id, []).append((frame["frame"], boxes[box_index]))
        active = [(assignment[i], boxes[i]) for i in range(len(boxes))]
    return tracks, next_id - 1


def write_metrics(
    path: Path,
    stem: str,
    tracks: dict[int, list[Observation]],
    keep: dict[int, int],
) -> int:
    """Write the full-rate ground truth used for scoring.

    The labelme export is deliberately sparse so a person can review it. Scoring
    against that sparse file would be wrong: the prediction carries a box on every
    frame, so the ground truth has to as well, or every unannotated frame counts
    against the tracker as a false positive and a false negative at once.
    """
    payload = {
        "video": stem,
        "identities": {
            f"mango_{identity:03d}": [
                {"frame": frame_id, "bbox": list(box)} for frame_id, box in observations
            ]
            for raw_id, observations in tracks.items()
            if raw_id in keep
            for identity in [keep[raw_id]]
        },
    }
    path.write_text(json.dumps(payload))
    return sum(len(v) for v in payload["identities"].values())


def export(
    video: Path,
    images: Path,
    stem: str,
    frames: list[dict],
    tracks: dict[int, list[Observation]],
    keep: dict[int, int],
    width: int,
    height: int,
    stride: int,
) -> list[dict]:
    """Write the labelme file and its frame images."""
    by_frame: dict[int, list[Observation]] = {}
    for raw_id, observations in tracks.items():
        if raw_id not in keep:
            continue
        identity = keep[raw_id]
        for frame_id, box in observations:
            by_frame.setdefault(frame_id, []).append((identity, box))

    capture = cv2.VideoCapture(str(video))
    items: list[dict] = []
    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index % stride == 0 and frame_index in by_frame:
            frame = cv2.resize(frame, (width, height))
            name = f"{stem}_f{frame_index:05d}.jpg"
            cv2.imwrite(str(images / name), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            shapes = [
                {
                    "label": f"mango_{identity:03d}",
                    "points": [[box[0], box[1]], [box[0] + box[2], box[1] + box[3]]],
                    "group_id": None,
                    "shape_type": "rectangle",
                    "flags": {},
                }
                for identity, box in sorted(by_frame[frame_index])
            ]
            items.append(
                {
                    "imagePath": name,
                    "imageHeight": height,
                    "imageWidth": width,
                    "shapes": shapes,
                }
            )
        frame_index += 1
    capture.release()
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--detections", type=Path, default=Path("data/gt/detections.json")
    )
    parser.add_argument("--videos", type=Path, default=Path("videos"))
    parser.add_argument("--out", type=Path, default=Path("data/gt/labelme"))
    parser.add_argument(
        "--metrics",
        type=Path,
        default=Path("data/gt/ground_truth"),
        help="full-rate scoring files",
    )
    parser.add_argument(
        "--stride", type=int, default=10, help="frames between exported frames"
    )
    parser.add_argument("--match-threshold", type=float, default=0.3)
    parser.add_argument(
        "--min-track-length",
        type=int,
        default=50,
        help="tracks shorter than this many frames are treated as annotation noise",
    )
    args = parser.parse_args()

    images = args.out / "images"
    images.mkdir(parents=True, exist_ok=True)
    args.metrics.mkdir(parents=True, exist_ok=True)
    detections = json.loads(args.detections.read_text())

    summary = {}
    for name, data in detections.items():
        stem = Path(name).stem
        video = args.videos / name
        frames = data["frames"]
        tracks, raw_count = associate(frames, args.match_threshold)

        lengths = {track_id: len(obs) for track_id, obs in tracks.items()}
        survivors = sorted(
            (t for t, n in lengths.items() if n >= args.min_track_length),
            key=lambda t: min(f for f, _ in tracks[t]),
        )
        keep = {track_id: index for index, track_id in enumerate(survivors, start=1)}
        dropped = raw_count - len(keep)

        items = export(
            video,
            images,
            stem,
            frames,
            tracks,
            keep,
            data["width"],
            data["height"],
            args.stride,
        )
        (args.out / f"{stem}.json").write_text(json.dumps(items, indent=1))
        boxes = write_metrics(args.metrics / f"{stem}.json", stem, tracks, keep)

        max_concurrent = max(
            (len(f["detections"]) for f in frames),
            default=0,
        )
        summary[stem] = {
            "frames": len(frames),
            "raw_identities": raw_count,
            "kept_identities": len(keep),
            "dropped_below_min_length": dropped,
            "annotated_frames": len(items),
            "full_rate_boxes": boxes,
            "boxes": sum(len(image["shapes"]) for image in items),
            "max_concurrent_detections": max_concurrent,
        }
        print(
            f"{stem}: {raw_count} raw ids -> {len(keep)} kept "
            f"(>= {args.min_track_length} frames), {dropped} dropped, "
            f"{len(items)} annotated frames, max {max_concurrent} concurrent detections"
        )

    (args.out.parent / "ground_truth_build.json").write_text(
        json.dumps(summary, indent=2)
    )
    print(f"\nwrote {args.out}, {args.metrics} and ground_truth_build.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
