"""Evaluate the trained YOLOv8 detector on the held-out test split.

Loads the fine-tuned ``best.pt`` through the project's :class:`YoloDetector`
adapter, runs it on every image in ``Mango_Dataset2/test``, and compares
predictions against the YOLO-format ground-truth labels at IoU >= 0.5.

The YOLO label format is ``class x_center y_center w h`` with normalized
coordinates, same as the detection input is ``(w, h)`` centered boxes in
normalized space, so we convert predictions to that space for comparison.

Args (all optional):
    --model: Path to weights file (default ``models/mango_yolov8n/weights/best.pt``).
    --test-images: Directory of test images.
    --test-labels: Directory of test labels.
    --conf: Confidence threshold (default 0.25).
    --iou: IoU threshold for a correct match (default 0.50).
    --samples: Number of annotated sample images to write (default 8).
    --outdir: Where to write annotated samples (default ``.tmp/detector_eval``).
"""

from __future__ import annotations

import argparse
import pathlib
from dataclasses import dataclass

import cv2
import numpy as np
from orchardvision_ml.detection import YoloDetector


@dataclass(frozen=True, slots=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def x1(self) -> float:
        return self.x - self.w / 2.0

    @property
    def y1(self) -> float:
        return self.y - self.h / 2.0

    @property
    def x2(self) -> float:
        return self.x + self.w / 2.0

    @property
    def y2(self) -> float:
        return self.y + self.h / 2.0


def iou(a: Box, b: Box) -> float:
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0.0 else 0.0


def load_gt(label_path: pathlib.Path) -> list[Box]:
    boxes: list[Box] = []
    if not label_path.exists():
        return boxes
    for line in label_path.read_text().splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        _, cx, cy, w, h = parts
        boxes.append(Box(float(cx), float(cy), float(w), float(h)))
    return boxes


def match_predictions(
    gt: list[Box], pred: list[Box], iou_threshold: float
) -> tuple[int, int, int, float]:
    """Greedy IoU matching -> (tp, fp, fn, m_iou_of_tp)."""
    tp = 0
    used_gt: set[int] = set()
    matched_iou: list[float] = []
    for p in pred:
        best_i = -1
        best_score = iou_threshold
        for i, g in enumerate(gt):
            if i in used_gt:
                continue
            score = iou(p, g)
            if score >= best_score:
                best_score = score
                best_i = i
        if best_i >= 0:
            used_gt.add(best_i)
            tp += 1
            matched_iou.append(best_score)
    fp = len(pred) - tp
    fn = len(gt) - tp
    mean_tp_iou = sum(matched_iou) / len(matched_iou) if matched_iou else 0.0
    return tp, fp, fn, mean_tp_iou


def parse_args() -> argparse.Namespace:
    repo = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        type=pathlib.Path,
        default=repo / "models" / "mango_yolov8n-4" / "weights" / "best.pt",
    )
    parser.add_argument("--test-images", type=pathlib.Path, default=None)
    parser.add_argument("--test-labels", type=pathlib.Path, default=None)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.50)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument(
        "--outdir", type=pathlib.Path, default=repo / ".tmp" / "detector_eval"
    )
    args = parser.parse_args()

    data = repo / "data" / "Mango_Dataset2"
    args.test_images = args.test_images or data / "test" / "images"
    args.test_labels = args.test_labels or data / "test" / "labels"
    return args


def draw_box(
    frame: np.ndarray, box: Box, color: tuple[int, int, int], label: str
) -> None:
    h, w = frame.shape[:2]
    x1 = int(box.x1 * w)
    y1 = int(box.y1 * h)
    x2 = int(box.x2 * w)
    y2 = int(box.y2 * h)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.putText(
        frame,
        label,
        (x1, max(y1 - 5, 15)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA,
    )


def main() -> None:
    args = parse_args()
    detector = YoloDetector(str(args.model), conf_threshold=args.conf)

    images = sorted(args.test_images.glob("*.jpg")) + sorted(
        args.test_images.glob("*.png")
    )
    if not images:
        raise SystemExit(f"No images found in {args.test_images}")

    total_tp = total_fp = total_fn = 0
    per_image: list[tuple[float, float, int]] = []  # (precision, recall, gt_count)
    worst: list[tuple[float, pathlib.Path]] = []
    annotated: list[pathlib.Path] = []
    args.outdir.mkdir(parents=True, exist_ok=True)

    for path in images:
        frame = cv2.imread(str(path))
        if frame is None:
            continue
        gt = load_gt(args.test_labels / f"{path.stem}.txt")
        result = detector.detect(frame, 0)
        pred = [
            (
                Box(
                    (x + w / 2.0) / frame.shape[1],
                    (y + h / 2.0) / frame.shape[0],
                    w / frame.shape[1],
                    h / frame.shape[0],
                ),
                conf,
            )
            for x, y, w, h, conf in ((*d.bbox, d.confidence) for d in result.detections)
        ]

        tp, fp, fn, _ = match_predictions(gt, [b for b, _ in pred], args.iou)
        total_tp += tp
        total_fp += fp
        total_fn += fn

        prec = tp / (tp + fp) if tp + fp else 1.0
        rec = tp / (tp + fn) if tp + fn else 1.0
        per_image.append((prec, rec, len(gt)))
        worst.append((rec, path))

        if len(annotated) < args.samples:
            for g in gt:
                draw_box(frame, g, (0, 255, 0), "gt")
            for box, conf in pred:
                draw_box(frame, box, (0, 0, 255), f"{conf:.2f}")
            annotated.append(path)
            cv2.imwrite(str(args.outdir / f"{path.stem}.png"), frame)

    worst.sort(key=lambda item: item[0])
    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    print("=" * 60)
    print(f"Model      : {detector.name}")
    print(f"Confidence : {args.conf}   IoU threshold: {args.iou}")
    print(f"Images     : {len(images)}")
    print("-" * 60)
    print(f"Total TP   : {total_tp}")
    print(f"Total FP   : {total_fp}")
    print(f"Total FN   : {total_fn}")
    print(f"Precision  : {precision:.4f}")
    print(f"Recall     : {recall:.4f}")
    print(f"F1         : {f1:.4f}")
    print("=" * 60)

    print("\nWorst 5 images (poorest recall):")
    for rec, path in worst[:5]:
        print(f"  {path.name}: recall={rec:.2f}")
    print(f"\nAnnotated samples written to {args.outdir}")

    perfect_prec = sum(prec for prec, _, _ in per_image if prec == 1.0)
    print(f"Images with perfect precision: {perfect_prec}/{len(per_image)}")


if __name__ == "__main__":
    main()
