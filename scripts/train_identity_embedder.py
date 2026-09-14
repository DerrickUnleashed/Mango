"""Self-supervised identity embedding training script (GPU).

Trains the identity embedding network on pseudo-labeled tracklets extracted from
your own footage — no manual identity annotation needed. Each round the current
model embeds every observation, DBSCAN clusters sub-tracklet centroids into
pseudo identities, contrastive pairs are built from those labels, and the
network is fine-tuned further. A self-paced confidence gate admits noisier
pseudo labels over rounds.

Corpus format (JSONL, one observation per line)::

    {"track_id": 1, "frame_id": 5, "bbox": [100, 100, 30, 30],
     "confidence": 0.9, "is_occluded": false, "source_id": "cam0"}

Frame videos live in ``--videos-dir`` named ``<source_id>.mp4`` (any cv2-readable
extension works). Produces a checkpoint loadable by ``IdentityEmbeddingNet``.

Usage: ``python scripts/train_identity_embedder.py --corpus data/tracks.jsonl \\
    --videos-dir data/videos --out-model models/identity/embedder.pt --repeats 3``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray
from orchardvision_ml.identity.dataset import TrackObservation
from orchardvision_ml.identity.pseudo_trainer import (
    SelfSupervisedConfig,
    SelfSupervisedTrainer,
)
from orchardvision_ml.identity.torch_trainer import (
    FrameProvider,
    TorchTrainerConfig,
)
from orchardvision_ml.identity.training import PairOptions


def _load_corpus(path: Path) -> list[TrackObservation]:
    observations: list[TrackObservation] = []
    with path.open() as handle:
        for line in handle:
            row = json.loads(line)
            bbox = tuple(float(v) for v in row["bbox"])
            observations.append(
                TrackObservation(
                    track_id=int(row["track_id"]),
                    frame_id=int(row["frame_id"]),
                    bbox=bbox,
                    confidence=float(row["confidence"]),
                    is_occluded=bool(row.get("is_occluded", False)),
                    source_id=str(row.get("source_id", "")),
                )
            )
    return observations


def _make_frame_provider(videos_dir: Path) -> FrameProvider:
    captures: dict[str, cv2.VideoCapture] = {}

    def provider(source_id: str, frame_id: int) -> NDArray[np.uint8]:
        source_id = source_id or "default"
        if source_id not in captures:
            candidates = list(videos_dir.glob(f"{source_id}.*"))
            if not candidates:
                raise FileNotFoundError(
                    f"no video for source_id={source_id!r} in {videos_dir}"
                )
            captures[source_id] = cv2.VideoCapture(str(candidates[0]))
        capture = captures[source_id]
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"could not read frame {frame_id} from {source_id}")
        return frame

    return provider


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus", type=Path, required=True, help="JSONL track observations"
    )
    parser.add_argument(
        "--videos-dir", type=Path, required=True, help="Videos named <source_id>.*"
    )
    parser.add_argument("--out-model", type=Path, required=True, help="Checkpoint path")

    parser.add_argument("--backbone", default="resnet18")
    parser.add_argument("--embed-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=512)
    parser.add_argument("--input-size", type=int, default=224)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--device", default=None, help="torch device (default: auto)")

    parser.add_argument("--cluster-eps", type=float, default=0.3)
    parser.add_argument("--cluster-min-samples", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--min-confidence", type=float, default=0.85)
    parser.add_argument("--confidence-floor", type=float, default=0.5)
    parser.add_argument("--confidence-decay", type=float, default=0.95)

    parser.add_argument("--max-frames-apart", type=int, default=15)
    parser.add_argument("--min-center-distance", type=float, default=60.0)
    parser.add_argument("--hard-mining-top-k", type=int, default=8)
    parser.add_argument("--negative-batch-size", type=int, default=32)
    args = parser.parse_args()

    if not args.corpus.is_file():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 2
    if not args.videos_dir.is_dir():
        print(f"videos dir not found: {args.videos_dir}", file=sys.stderr)
        return 2

    observations = _load_corpus(args.corpus)
    if not observations:
        print(f"no observations in {args.corpus}", file=sys.stderr)
        return 2

    config = SelfSupervisedConfig(
        cluster_eps=args.cluster_eps,
        cluster_min_samples=args.cluster_min_samples,
        repeats=args.repeats,
        initial_min_confidence=args.min_confidence,
        confidence_floor=args.confidence_floor,
        confidence_decay=args.confidence_decay,
        pair_options=PairOptions(
            max_frames_apart=args.max_frames_apart,
            min_center_distance=args.min_center_distance,
            hard_mining_top_k=args.hard_mining_top_k,
            negative_batch_size=args.negative_batch_size,
        ),
        base_config=TorchTrainerConfig(
            backbone=args.backbone,
            embed_dim=args.embed_dim,
            hidden_dim=args.hidden_dim,
            input_size=args.input_size,
            temperature=args.temperature,
            learning_rate=args.learning_rate,
            epochs=args.epochs,
            batch_size=args.batch_size,
            device=args.device,
        ),
    )

    trainer = SelfSupervisedTrainer(config)
    frames = _make_frame_provider(args.videos_dir)
    print(
        f"training on {len(observations)} observations, {config.repeats} curriculum rounds"
    )
    result = trainer.train(observations, frames)

    for index, round_result in enumerate(result.rounds, start=1):
        train = round_result.training
        print(
            f"round {index}: conf>= {round_result.threshold:.2f} "
            f"labeled={round_result.labeled_tracklets} "
            f"unlabeled={round_result.unlabeled_tracklets} "
            f"clusters={round_result.clusters} anchors={round_result.anchors} "
            f"loss={train.loss_history[-1]:.4f} "
            f"pos={train.positive_similarity:.3f} neg={train.negative_similarity:.3f}"
        )
    print(f"final separation: {result.final_separation():.4f}")

    args.out_model.parent.mkdir(parents=True, exist_ok=True)
    trainer.save(args.out_model)
    print(f"saved checkpoint to {args.out_model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
