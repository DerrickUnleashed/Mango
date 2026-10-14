"""Render the Chapter 8 result figures from an evaluation export.

Reads the CSV/JSON written by ``scripts/evaluate_videos.py`` and produces the
plots used in the report. Provenance of the ground truth is printed alongside the
figures, because the identity-level metrics are only meaningful against a
corrected annotation.

Usage::

    uv run --project ml python scripts/plot_results.py --results data/results
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

VIDEO_ORDER = ["test", "test4", "Test3"]
VIDEO_LABEL = {"test": "V1 test.mp4", "test4": "V2 test4.mp4", "Test3": "V3 Test3.mp4"}


def read_rows(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def sort_videos(rows: list[dict]) -> list[str]:
    seen = [v for v in VIDEO_ORDER if any(r["video"] == v for r in rows)]
    return seen + [v for v in dict.fromkeys(r["video"] for r in rows) if v not in seen]


def plot_tracker_comparison(rows: list[dict], out: Path) -> None:
    videos = sort_videos(rows)
    trackers = list(dict.fromkeys(r["tracker"] for r in rows))
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4))
    metrics = [("idf1", "IDF1"), ("hota", "HOTA"), ("idSwitches", "ID switches")]
    width = 0.8 / len(trackers)
    for axis, (key, title) in zip(axes, metrics):
        for index, tracker in enumerate(trackers):
            values = [
                next(
                    (
                        float(r[key])
                        for r in rows
                        if r["video"] == video and r["tracker"] == tracker
                    ),
                    0.0,
                )
                for video in videos
            ]
            positions = [i + index * width for i in range(len(videos))]
            axis.bar(positions, values, width=width, label=tracker)
        axis.set_xticks(
            [i + width * (len(trackers) - 1) / 2 for i in range(len(videos))]
        )
        axis.set_xticklabels([VIDEO_LABEL.get(v, v) for v in videos], fontsize=8)
        axis.set_title(title, fontsize=10)
        axis.grid(axis="y", alpha=0.3)
        axis.set_axisbelow(True)
    axes[0].legend(fontsize=8)
    fig.suptitle(
        "Tracker comparison against full-rate ground truth built by scripts/build_ground_truth.py",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("wrote", out)


def plot_confidence_sweep(rows: list[dict], out: Path) -> None:
    videos = sort_videos(rows)
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.4))
    trackers = list(dict.fromkeys(r["tracker"] for r in rows))
    colors = {"mock": "#f59e0b", "bytetrack": "#22d3ee"}
    for tracker in trackers:
        for axis, key, title in zip(
            axes, ("predicted_tracks", "countMae"), ("Predicted tracks", "Count MAE")
        ):
            series = []
            for video in videos:
                points = sorted(
                    (float(r["confidence_threshold"]), float(r[key]))
                    for r in rows
                    if r["video"] == video and r["tracker"] == tracker
                )
                if points:
                    xs, ys = zip(*points)
                    series.append((xs, ys))
            for index, (xs, ys) in enumerate(series):
                axis.plot(
                    xs,
                    ys,
                    marker="o",
                    ms=3,
                    lw=1.4,
                    color=list(colors.values())[index % 2],
                    label=f"{tracker} · {VIDEO_LABEL.get(videos[index], videos[index])}",
                )
            axis.set_xlabel("detection confidence")
            axis.set_title(title, fontsize=10)
            axis.grid(alpha=0.3)
            axis.set_axisbelow(True)
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("wrote", out)


def plot_timing(timings_path: Path, out: Path) -> None:
    data = json.loads(timings_path.read_text())
    fig, axis = plt.subplots(figsize=(9.0, 3.2))
    for label, values in data.items():
        video, tracker, *_ = label.split("|")
        axis.plot(
            values,
            lw=0.9,
            alpha=0.85,
            label=f"{VIDEO_LABEL.get(video, video)} · {tracker}",
        )
    axis.set_xlabel("frame index")
    axis.set_ylabel("processing time (ms)")
    axis.set_title("Per-frame detection + tracking time", fontsize=10)
    axis.grid(alpha=0.3)
    axis.set_axisbelow(True)
    axis.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("wrote", out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("data/results"))
    parser.add_argument("--out", type=Path, default=Path("docs"))
    args = parser.parse_args()

    rows = read_rows(args.results / "metrics.csv")
    ground_truth = json.loads((args.results / "ground_truth.json").read_text())

    plot_tracker_comparison(rows, args.out / "tracker_comparison.png")
    plot_timing(args.results / "timings.json", args.out / "per_frame_timing.png")

    sweep_dir = args.results.parent / "results" / "sweep"
    if not sweep_dir.exists():
        sweep_dir = args.results / "sweep"
    if (sweep_dir / "metrics.csv").is_file():
        plot_confidence_sweep(
            read_rows(sweep_dir / "metrics.csv"), args.out / "confidence_sweep.png"
        )

    print("\nGround truth used for these figures:")
    for video, meta in ground_truth.items():
        print(
            f"  {video}: {meta['gt_identities']} identities over {meta['gt_frames']} frames, "
            f"{meta['gt_boxes']} boxes ({meta['boxes_per_identity']} per identity)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
