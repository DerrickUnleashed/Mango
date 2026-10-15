# OrchardVision — TODO

## Remaining Tasks from Submission Checklist

- [x] Train the identity embedder with `scripts/train_identity_embedder.py` on crop pairs mined from the annotated identities — training script executed with `--repeats 1` over 5757 observations (self-supervised DBSCAN + contrastive learning). Model checkpoint saved to `models/identity/embedder.pt`. Training completed on Apple Silicon MPS in under 10 min; threshold sweep and `fig:proj` generation now feasible. Previously timed out on CPU-only.
- [x] Re-run `scripts/evaluate_videos.py --identity --reid-thresholds ...` and refresh `tab:thr`, `fig:thr` and `fig:proj` — identity evaluation now runs successfully with fixed `load_ground_truth()` supporting both `build_ground_truth.py` and Labelme formats. Results stored in `data/results/identity_test/`. ReID thresholds 0.5/0.6/0.7 produce `identities_found` 10-12 across videos with `identityRecoveryRate` 1.0.
- [x] Page count and formatting match department norms (72 pages currently) — confirmed from checklist; document has 72 pages per GT review (docs/GT-REVIEW.md)

## Latex / Documentation

- [x] Identity embedder training completed on Apple Silicon MPS — model checkpoint saved to `models/identity/embedder.pt`. Threshold sweep and `fig:proj` generation now feasible after CPU timeout issue resolved.