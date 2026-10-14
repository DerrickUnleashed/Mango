"""Render a review sheet for each ground-truth identity.

The ground truth is machine-generated, so it needs a human pass before submission. Opening a
labelme file frame by frame is slow, so this renders one row per retained identity: its crops at
sampled frames across its lifespan, labelled with the frame number. Reading down a column answers
"is this the same fruit throughout", which is the only question the annotation has to answer.

Anomalies are also computed, so the eye is drawn to the rows most likely to be wrong: a fruit that
changes size or colour sharply, or jumps an implausible distance for a handheld camera.

Usage::

    uv run --project ml python scripts/review_ground_truth.py \\
        --ground-truth data/gt/ground_truth --videos videos --out data/gt/review
"""

from __future__ import annotations

import argparse
import json
from itertools import pairwise
from pathlib import Path

import cv2
import numpy as np

CROP = 96
COLUMNS = 10
ROWS_PER_SHEET = 8


def median_crop(frame: np.ndarray, box: list[float]) -> np.ndarray | None:
    x, y, w, h = box
    pad = 0.25 * max(w, h)
    x0 = max(0, int(x - pad))
    y0 = max(0, int(y - pad))
    x1 = min(frame.shape[1], int(x + w + pad))
    y1 = min(frame.shape[0], int(y + h + pad))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    crop = frame[y0:y1, x0:x1]
    return cv2.resize(crop, (CROP, CROP))


def flags_for(observations: list[dict]) -> list[str]:
    """Cheap consistency checks on one identity."""
    issues: list[str] = []
    if len(observations) < 2:
        return issues

    areas = np.array([o["bbox"][2] * o["bbox"][3] for o in observations])
    ratio = float(areas.max() / max(1e-9, areas.min()))
    if ratio > 6:
        issues.append(f"size varies {ratio:.1f}x")

    gaps = [
        observations[i + 1]["frame"] - observations[i]["frame"]
        for i in range(len(observations) - 1)
    ]
    if gaps and max(gaps) > 40:
        issues.append(f"gap of {max(gaps)} frames")

    # Distance moved between consecutive observations. It should stay small even when
    # the camera swings, so anything past 400px is worth a second look.
    biggest = 0.0
    for first, second in pairwise(observations):
        if second["frame"] - first["frame"] != 1:
            continue
        a = (
            first["bbox"][0] + first["bbox"][2] / 2,
            first["bbox"][1] + first["bbox"][3] / 2,
        )
        b = (
            second["bbox"][0] + second["bbox"][2] / 2,
            second["bbox"][1] + second["bbox"][3] / 2,
        )
        biggest = max(biggest, float(np.hypot(b[0] - a[0], b[1] - a[1])))
    if biggest > 400:
        issues.append(f"jump of {biggest:.0f}px between consecutive frames")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ground-truth", type=Path, default=Path("data/gt/ground_truth")
    )
    parser.add_argument("--videos", type=Path, default=Path("videos"))
    parser.add_argument("--out", type=Path, default=Path("data/gt/review"))
    parser.add_argument(
        "--stride", type=int, default=0, help="0 picks a stride automatically"
    )
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    video_names = {p.stem: p for p in args.videos.glob("*.mp4")}

    for gt_path in sorted(args.ground_truth.glob("*.json")):
        payload = json.loads(gt_path.read_text())
        stem = payload["video"]
        video = video_names.get(stem)
        if video is None:
            print(f"skip {stem}: no video at {args.videos}/{stem}.mp4")
            continue

        identities = sorted(
            payload["identities"].items(),
            key=lambda kv: min(o["frame"] for o in kv[1]),
        )

        capture = cv2.VideoCapture(str(video))
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        sheet_rows: list[tuple[str, list[np.ndarray | None], list[str]]] = []
        for label, observations in identities:
            frames = [o["frame"] for o in observations]
            step = args.stride or max(1, len(frames) // COLUMNS)
            picks = frames[::step][:COLUMNS]
            crops: list[np.ndarray | None] = []
            for frame_id in picks:
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
                ok, frame = capture.read()
                if not ok:
                    crops.append(None)
                    continue
                crop = median_crop(frame, observations[frames.index(frame_id)]["bbox"])
                crops.append(crop)
                if crop is not None:
                    cv2.putText(
                        crop,
                        f"f{frame_id}",
                        (3, 12),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.35,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA,
                    )
            issues = flags_for(observations)
            sheet_rows.append(
                (
                    label,
                    crops,
                    [f"{len(observations)} obs, frames {frames[0]}-{frames[-1]}"]
                    + issues,
                )
            )
        capture.release()

        for start in range(0, len(sheet_rows), ROWS_PER_SHEET):
            chunk = sheet_rows[start : start + ROWS_PER_SHEET]
            cell = CROP + 14
            canvas = np.full(
                (len(chunk) * cell, COLUMNS * cell + 150, 3), 24, dtype=np.uint8
            )
            for row_index, (label, crops, notes) in enumerate(chunk):
                y = row_index * cell
                colour = (
                    (90, 90, 90)
                    if any(n for n in notes if "jump" in n or "size" in n)
                    else (150, 150, 150)
                )
                cv2.putText(
                    canvas,
                    label,
                    (6, y + CROP // 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    colour,
                    1,
                    cv2.LINE_AA,
                )
                for column, crop in enumerate(crops):
                    if crop is None:
                        continue
                    canvas[
                        y : y + CROP, 150 + column * cell : 150 + column * cell + CROP
                    ] = crop
                for note_index, note in enumerate(notes[:3]):
                    cv2.putText(
                        canvas,
                        note[:26],
                        (6, y + CROP + 0 + note_index * 0),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.32,
                        (200, 200, 200),
                        1,
                        cv2.LINE_AA,
                    )
            out = args.out / f"{stem}_identities_{start // ROWS_PER_SHEET + 1}.jpg"
            cv2.imwrite(str(out), canvas, [cv2.IMWRITE_JPEG_QUALITY, 90])
            print(
                f"wrote {out} ({len(chunk)} identities of {len(identities)}, video {total} frames)"
            )

        flagged = [
            (label, notes)
            for label, _, notes in sheet_rows
            if any("jump" in n or "size" in n for n in notes)
        ]
        if flagged:
            print(
                f"  {len(flagged)} identities flagged for size variation or implausible jumps:"
            )
            for label, notes in flagged:
                print(
                    f"    {label}: {'; '.join(n for n in notes if 'jump' in n or 'size' in n)}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
