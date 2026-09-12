"""Fine-tune the mango detector on video-derived tiles (GPU).

Reads ``<out>/data.yaml`` produced by ``export_video_labels.py`` and fine-tunes
the current canopy-weak model (default: ``mango_yolov8n-4``) on canopy tiles so
small/hidden fruit in real camera footage becomes detectable. Copies the best
weights to ``models/mango_yolov8n-video/weights/best.pt`` and reports val mAP.

Usage: ``python scripts/train_video_model.py -o data/video_dataset --epochs 60``
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from ultralytics import YOLO


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("data/video_dataset"),
        help="Dataset root containing data.yaml",
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=Path("models/mango_yolov8n-4/weights/best.pt"),
        help="Checkpoint to fine-tune from",
    )
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=640, help="Train resolution")
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="0")
    parser.add_argument(
        "--out-model",
        type=Path,
        default=Path("models/mango_yolov8n-video/weights/best.pt"),
        help="Where to copy the best weights",
    )
    args = parser.parse_args()

    data = args.out / "data.yaml"
    if not data.is_file():
        print(f"data.yaml not found (run export_video_labels.py first): {data}", file=sys.stderr)
        return 2
    if not args.weights.is_file():
        print(f"start weights not found: {args.weights}", file=sys.stderr)
        return 2

    model = YOLO(str(args.weights))
    model.train(
        data=str(data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(args.out / "runs"),
        name="video-mango",
        exist_ok=True,
        patience=20,
        verbose=True,
    )

    best = args.out / "runs" / "video-mango" / "weights" / "best.pt"
    if best.is_file():
        args.out_model.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best, args.out_model)
        print(f"copied best weights to {args.out_model}")
        print(f"train results saved to {args.out / 'runs' / 'video-mango'}")
    else:
        print("training finished but best.pt not found under runs/", file=sys.stderr)
        return 1

    metrics = model.val(data=str(data), split="val", device=args.device, verbose=True)
    print(
        f"val mAP50={metrics.box.map50:.4f} mAP50-95={metrics.box.map:.4f} "
        f"precision={metrics.box.mp:.4f} recall={metrics.box.mr:.4f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())