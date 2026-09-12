"""Export a labelme-labeled tile set to YOLO-format labels + data.yaml.

Reads labelme JSON files saved next to tile images in ``<out>/tiles``, converts
each marked rectangle/polygon to a normalized YOLO line (class ``mango``=0) in
tile coordinates, then splits images+labels into ``train/`` and ``val/`` for
``ultralytics`` training.

Usage: ``python scripts/export_video_labels.py -o data/video_dataset``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CLASS_NAME = "mango"
CLASS_ID = 0
VAL_FRACTION = 0.15


def _box_from_shape(shape: dict, w: int, h: int) -> tuple[float, float, float, float]:
    stype = shape["shape_type"]
    pts = shape["points"]
    if stype == "rectangle" and len(pts) == 2:
        (x0, y0), (x1, y1) = pts
    else:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return (
        min(x0, x1) / w,
        min(y0, y1) / h,
        max(x0, x1) / w,
        max(y0, y1) / h,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("data/video_dataset"),
        help="Dataset root (contains tiles/ and images/)",
    )
    parser.add_argument("--include-base", action="store_true", help="Merge Mango_Dataset2 into train")
    args = parser.parse_args()

    tiles = args.out / "tiles"
    if not tiles.is_dir():
        print(f"tiles dir not found: {tiles}", file=sys.stderr)
        return 2

    records: list[tuple[str, list[tuple[float, float, float, float]]]] = []
    for json_path in sorted(tiles.glob("*.json")):
        if json_path.name == "index.json":
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"skipping unparseable {json_path.name}: {exc}", file=sys.stderr)
            continue
        image_name = Path(data.get("imagePath", "")).name
        image_path = tiles / image_name
        if not image_path.is_file():
            continue
        image = __import__("cv2").imread(str(image_path))
        if image is None:
            continue
        h, w = image.shape[:2]
        boxes = []
        for shape in data.get("shapes", []):
            label = shape.get("label", "").strip().lower()
            if label != CLASS_NAME:
                continue
            boxes.append(_box_from_shape(shape, w, h))
        records.append((image_path, boxes))

    if not records:
        print("no labeled tiles found; run labelme first", file=sys.stderr)
        return 1

    labeled = [r for r in records if r[1]]
    empty = [r for r in records if not r[1]]
    print(
        f"labelme export: {len(labeled)} tiles with boxes "
        f"({sum(len(b) for _, b in labeled)} objects), {len(empty)} background tiles"
    )

    all_records = labeled + empty
    val_count = max(1, int(len(all_records) * VAL_FRACTION))

    def write_split(split_dir: Path, items: list[tuple[Path, list]]) -> int:
        imgs = split_dir / "images"
        lbls = split_dir / "labels"
        imgs.mkdir(parents=True, exist_ok=True)
        lbls.mkdir(parents=True, exist_ok=True)
        objects = 0
        for image_path, boxes in items:
            target = imgs / image_path.name
            target.write_bytes(image_path.read_bytes())
            (lbls / image_path.with_suffix(".txt").name).write_text(
                "".join(f"{CLASS_ID} {x0:.6f} {y0:.6f} {x1:.6f} {y1:.6f}\n" for x0, y0, x1, y1 in boxes)
            )
            objects += len(boxes)
        return objects

    val_items = all_records[:val_count]
    train_items = all_records[val_count:]

    if args.include_base:
        base_dir = Path("data/Mango_Dataset2")
        train_items = train_items + _base_items(base_dir, "train") + _base_items(base_dir, "valid")
        val_items = val_items + _base_items(base_dir, "test")
        print(f"base dataset merged: train {len(train_items)} imgs, val {len(val_items)} imgs")

    write_split(args.out / "train", train_items)
    val_objects = write_split(args.out / "val", val_items)
    train_objects = sum(len(b) for _, b in train_items)
    print(f"train: {len(train_items)} images ({train_objects} objects), "
          f"val: {len(val_items)} images ({val_objects} objects)")

    # support images that reference the base splits without copying when present
    (args.out / "data.yaml").write_text(
        f"path: {args.out.resolve().as_posix()}\n"
        "train: train/images\n"
        "val: val/images\n\n"
        f"nc: 1\nnames: [{CLASS_NAME!r}]\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out / 'data.yaml'}")
    return 0


def _base_items(base_dir: Path, split: str) -> list[tuple[Path, list[tuple[float, float, float, float]]]]:
    imgs = base_dir / split / "images"
    lbls = base_dir / split / "labels"
    items: list[tuple[Path, list[tuple[float, float, float, float]]]] = []
    if not imgs.is_dir():
        return items
    for image_path in sorted(imgs.glob("*.*")):
        boxes: list[tuple[float, float, float, float]] = []
        lbl = lbls / image_path.with_suffix(".txt").name
        if lbl.is_file():
            for line in lbl.read_text().splitlines():
                parts = line.split()
                if len(parts) == 5:
                    boxes.append(tuple(float(p) for p in parts[1:]))
        items.append((image_path, boxes))
    return items


if __name__ == "__main__":
    sys.exit(main())