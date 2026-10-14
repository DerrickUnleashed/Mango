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


def plot_reid_sweep(rows: list[dict], out: Path) -> None:
    """Identities found and accepted re-identifications against the ReID threshold."""
    videos = sort_videos(rows)
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.4))
    for axis, key, title in zip(
        axes,
        ("identities_found", "reid_accepted"),
        ("Identities found", "Accepted re-identifications"),
    ):
        for video in videos:
            points = sorted(
                (float(r["reid_threshold"]), float(r[key]))
                for r in rows
                if r["video"] == video
            )
            if points:
                axis.plot(
                    *zip(*points),
                    marker="o",
                    ms=3,
                    lw=1.4,
                    label=VIDEO_LABEL.get(video, video),
                )
        axis.set_xlabel("ReID similarity threshold")
        axis.set_title(title, fontsize=10)
        axis.grid(alpha=0.3)
        axis.set_axisbelow(True)
    axes[1].legend(fontsize=7)
    fig.suptitle(
        "Re-identification threshold sweep (ByteTrack, track buffer 5 frames)",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("wrote", out)


def plot_motion_ablation(rows: list[dict], out: Path) -> None:
    """Effect of compensating measured camera motion on identity continuity."""
    videos = sort_videos(rows)
    motions = list(dict.fromkeys(r["camera_motion"] for r in rows))
    fig, axis = plt.subplots(figsize=(7.0, 3.2))
    width = 0.8 / len(motions)
    metrics = [
        ("idf1", "IDF1"),
        ("hota", "HOTA"),
        ("idSwitches", "ID switches (lower is better)"),
    ]
    for index, (key, title) in enumerate(metrics):
        scale = 100 if key != "idSwitches" else 1
        for position, motion in enumerate(motions):
            values = [
                next(
                    (
                        float(r[key])
                        for r in rows
                        if r["video"] == video and r["camera_motion"] == motion
                    ),
                    0.0,
                )
                for video in videos
            ]
            offset = (position - (len(motions) - 1) / 2) * width
            bars = axis.bar(
                [index * 1.6 + p + offset for p in range(len(videos))],
                [v * scale for v in values],
                width=width,
                label=f"{motion} · {title}",
            )
            axis.bar_label(bars, fontsize=6, fmt="%.2f")
        axis.set_xticks(
            [index * 1.6 + (len(videos) - 1) / 2 for index in range(len(metrics))]
        )
        axis.set_xticklabels([t for _, t in metrics], fontsize=9)
        axis.set_yscale("symlog", linthresh=1)
    axis.grid(axis="y", alpha=0.3)
    axis.set_axisbelow(True)
    axis.legend(fontsize=7)
    fig.suptitle("Camera-motion compensation, averaged over V1-V3", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("wrote", out)


def principal_components(matrix):
    """First two principal components, so no extra dependency is needed."""
    import numpy as np

    centred = matrix - matrix.mean(axis=0, keepdims=True)
    _, _, right = np.linalg.svd(centred, full_matrices=False)
    return centred @ right[:2].T


def plot_prototypes(identities: dict, out: Path) -> None:
    """Two-dimensional projection of the identity prototypes of one video."""
    import numpy as np

    key = next(iter(identities))
    vectors = [np.array(v) for v in identities[key]["prototypes"].values()]
    if len(vectors) < 2:
        print("not enough prototypes to project")
        return
    matrix = np.stack(vectors)
    coords = principal_components(matrix)
    fig, axis = plt.subplots(figsize=(5.2, 4.0))
    axis.scatter(
        coords[:, 0], coords[:, 1], s=90, c="#f59e0b", edgecolors="black", zorder=3
    )
    for index, (coord, point) in enumerate(zip(coords, matrix, strict=True), start=1):
        axis.annotate(
            f"#{index}", coord, textcoords="offset points", xytext=(6, 4), fontsize=8
        )
    axis.set_xlabel("PC1")
    axis.set_ylabel("PC2")
    axis.set_title(
        f"Identity prototypes, PCA projection\n{VIDEO_LABEL.get(identities[key]['video'], identities[key]['video'])} "
        f"({len(vectors)} identities)",
        fontsize=9,
    )
    axis.grid(alpha=0.3)
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

    reid_dir = args.results / "reid"
    if (reid_dir / "metrics.csv").is_file():
        plot_reid_sweep(
            read_rows(reid_dir / "metrics.csv"), args.out / "reid_threshold_sweep.png"
        )

    motion_dir = args.results / "motion"
    if (motion_dir / "metrics.csv").is_file():
        plot_motion_ablation(
            read_rows(motion_dir / "metrics.csv"), args.out / "motion_ablation.png"
        )
        identities_path = motion_dir / "identities.json"
        if identities_path.is_file():
            plot_prototypes(
                json.loads(identities_path.read_text()),
                args.out / "identity_prototypes.png",
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
