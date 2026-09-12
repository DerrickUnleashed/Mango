"""Build a label-ready video dataset for fine-tuning the mango detector.

Extracts stride-sampled frames from an orchard video, slices each frame into a
grid of label-friendly tiles (small/hidden fruit is hard to box at full
resolution), and runs a low-confidence tiled detection pass so existing boxes
show up as suggestions for a quick prune-edit (the current canopy-trained model
finds few, so most boxes will be drawn by hand).

Pipeline:
    1. ``labelme data/video_dataset/tiles``  (pip install labelme)
    2. Draw "mango" rectangles, save each image's JSON next to the image.
    3. ``python scripts/export_video_labels.py -o data/video_dataset``
    4. ``python scripts/train_video_model.py -o data/video_dataset``
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2

TILE_OVERLAP = 0.10
SUGGEST_MAX_AREA_RATIO = 0.5
CORNER_STEP = 4


def _tile_layout(w: int, h: int, cols: int, rows: int, overlap: float):
    tw, th = w / cols, h / rows
    pad_x, pad_y = int(tw * overlap), int(th * overlap)
    for gy in range(rows):
        for gx in range(cols):
            x0 = max(0, int(gx * tw - pad_x))
            y0 = max(0, int(gy * th - pad_y))
            x1 = min(w, int((gx + 1) * tw + pad_x))
            y1 = min(h, int((gy + 1) * th + pad_y))
            yield gx, gy, (x0, y0, x1, y1)


def _suggest(
    frame, tiles, model, conf: float, device: str | None
) -> dict[str, list[list[float]]]:
    """Run low-conf tiled detection; return tile-name -> list of xyxy boxes."""
    suggestions: dict[str, list[list[float]]] = {}
    model_boxes: dict = {}
    if model is None:
        return suggestions
    for gx, gy, (x0, y0, x1, y1) in tiles:
        tile = frame[y0:y1, x0:x1]
        if tile.shape[0] < 32 or tile.shape[1] < 32:
            continue
        r = model.predict(
            source=cv2.cvtColor(tile, cv2.COLOR_BGR2RGB),
            conf=conf,
            iou=0.35,
            device=device,
            verbose=False,
        )
        boxes = r[0].boxes
        if boxes is None or len(boxes) == 0:
            continue
        confs = boxes.conf.cpu().numpy()
        for i, b in enumerate(boxes.xyxy.cpu().numpy()):
            xl, yl, xr, yr = b
            area = (xr - xl) * (yr - yl)
            if area > SUGGEST_MAX_AREA_RATIO * tile.shape[0] * tile.shape[1]:
                continue
            model_boxes.setdefault((gx, gy, (x0, y0, x1, y1)), []).append(
                [float(xl) + x0, float(yl) + y0, float(xr) + x0, float(yr) + y0, float(confs[i])]
            )
    # merge overlapping suggestions across adjacent tiles back to frame coords
    hits: list[tuple[float, float, float, float, float]] = []
    for boxes in model_boxes.values():
        hits.extend(b for b in boxes)
    if not hits:
        return suggestions
    order = sorted(enumerate(hits), key=lambda item: -item[1][4])
    kept: list[tuple[float, float, float, float, float]] = []
    for _, box in order:
        if all(_iou(box, k) < 0.4 for k in kept):
            kept.append(box)
    for frame_xyxy in kept:
        for gx, gy, (x0, y0, x1, y1) in tiles:
            if _intersects(frame_xyxy, (x0, y0, x1, y1)):
                name = f"tile_{gx}_{gy}"
                clipped = [_clip_box(frame_xyxy, (x0, y0, x1, y1))]
                suggestions.setdefault(name, []).extend(clipped)
    return suggestions


def _iou(a, b):
    ax0, ay0, ax1, ay1, _ = a
    bx0, by0, bx1, by1, _ = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    if inter == 0:
        return 0.0
    union = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / union


def _intersects(a, tile):
    ax0, ay0, ax1, ay1, _ = a
    bx0, by0, bx1, by1 = tile
    return max(0, min(ax1, bx1) - max(ax0, bx0)) > 0 and max(0, min(ay1, by1) - max(ay0, by0)) > 0


def _clip_box(a, tile):
    bx0, by0, bx1, by1 = tile
    return [
        max(bx0, min(a[0], bx1)),
        max(by0, min(a[1], by1)),
        max(bx0, min(a[2], bx1)),
        max(by0, min(a[3], by1)),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("data/video_dataset"),
        help="Output dataset directory (created if missing)",
    )
    parser.add_argument("--stride", type=int, default=20, help="Sample every Nth frame")
    parser.add_argument(
        "--max-frames", type=int, default=0, help="Stop after this many sampled frames (0 = all)"
    )
    parser.add_argument("--tiles", type=int, default=2, help="Tile grid size (N x N)")
    parser.add_argument(
        "--suggest-conf",
        type=float,
        default=0.08,
        help="Confidence for the auto-suggestion pass (0 disables)",
    )
    parser.add_argument("--device", default="0", help="Inference device for suggestions")
    args = parser.parse_args()

    if not args.video.is_file():
        print(f"video not found: {args.video}", file=sys.stderr)
        return 2

    out = args.out
    images = out / "images"
    tiles = out / "tiles"
    suggestions_dir = out / "suggestions"
    for d in (images, tiles, suggestions_dir):
        d.mkdir(parents=True, exist_ok=True)

    model = None
    if args.suggest_conf > 0:
        try:
            from ultralytics import YOLO
        except ModuleNotFoundError:
            print("ultralytics not installed; skipping suggestion pass", file=sys.stderr)
        else:
            model = YOLO(
                os.environ.get("YOLO_WEIGHTS_PATH")
                or "models/mango_yolov8n-4/weights/best.pt"
            )

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        print("could not open video", file=sys.stderr)
        return 2
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    grid = args.tiles

    frame_index = 0
    sampled = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % args.stride != 0:
            frame_index += 1
            continue
        image_stem = f"frame_{frame_index:05d}"
        image_path = images / f"{image_stem}.jpg"
        cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])

        H, W = frame.shape[:2]
        for gx, gy, (x0, y0, x1, y1) in _tile_layout(W, H, grid, grid, TILE_OVERLAP):
            tile_name = f"{image_stem}_t{gx}_{gy}"
            cv2.imwrite(str(tiles / f"{tile_name}.jpg"), frame[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 92])

        sampled += 1
        frame_index += 1
        if args.max_frames and sampled >= args.max_frames:
            break
    cap.release()
    print(f"extracted {sampled} frames ({total} available, stride {args.stride})")

    if model is not None:

        def tick():
            cap2 = cv2.VideoCapture(str(args.video))
            frame_index = 0
            sampled2 = 0
            while True:
                ok2, frame = cap2.read()
                if not ok2:
                    break
                if frame_index % args.stride == 0:
                    yield frame_index, frame
                    sampled2 += 1
                    if args.max_frames and sampled2 >= args.max_frames:
                        break
                frame_index += 1
            cap2.release()

        total_suggestions = 0
        for frame_index, frame in tick():
            H, W = frame.shape[:2]
            tiles_layout = list(_tile_layout(W, H, grid, grid, TILE_OVERLAP))
            sugg = _suggest(frame, tiles_layout, model, args.suggest_conf, args.device)
            total_suggestions += sum(len(b) for b in sugg.values())
            meta = {"suggestions": sugg}
            (suggestions_dir / f"frame_{frame_index:05d}.json").write_text(json.dumps(meta))
            if sugg:
                overlay = frame.copy()
                for name, boxes in sugg.items():
                    _, _, (x0, y0, x1, y1) = next(
                        t for t in tiles_layout if f"tile_{t[0]}_{t[1]}" == name
                    )
                    for bx0, by0, bx1, by1 in boxes:
                        cv2.rectangle(overlay, (int(bx0), int(by0)), (int(bx1), int(by1)), (0, 255, 0), 2)
                cv2.imwrite(str(suggestions_dir / f"frame_{frame_index:05d}.jpg"), overlay)
        print(f"suggestion pass: {total_suggestions} candidate boxes across {sampled} frames")

    (out / "README.md").write_text(
        _readme(grid),
        encoding="utf-8",
    )
    return 0


def _readme(grid: int) -> str:
    return f"""# Video labeling dataset

Label the tiles to create training boxes for the real-camera mango model.

1. Install labelme:  `pip install labelme`
2. Open the tiles:   `labelme data/video_dataset/tiles`
3. For each image, draw rectangles around mango fruit and set the label to
   `mango`. Save (Ctrl-S / the save button). Save the JSON *into* the tiles
   directory so it sits next to its image.
4. Optional: `data/video_dataset/suggestions/frame_*.jpg` contains auto-boxes
   drawn by the current model at a very low threshold; the model was trained on
   close-up shots so it rarely proposes fruit in canopy tiles. Check them, keep
   or delete, and hand-add the rest. Most of the work is manual - the tiles are
   a {grid}x{grid} crop grid so the small/hidden fruit is big enough to see.
5. Export labels:

       python scripts/export_video_labels.py -o data/video_dataset

6. Train on the GPU:

       python scripts/train_video_model.py -o data/video_dataset
"""


if __name__ == "__main__":
    sys.exit(main())