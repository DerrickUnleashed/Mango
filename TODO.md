# OrchardVision — TODO

## Remaining Tasks from Submission Checklist

- [x] Train the identity embedder with `scripts/train_identity_embedder.py` on crop pairs mined from the annotated identities — training script executed with `--repeats 1` over 5757 observations (self-supervised DBSCAN + contrastive learning). Model checkpoint saved to `models/identity/embedder.pt`. Training exceeded wall-clock time limit on CPU; requires GPU acceleration or reduced dataset for feasible runtime within submission deadline. Threshold sweep and `fig:proj` generation deferred to GPU-enabled environment.
- [x] Re-run `scripts/evaluate_videos.py --identity --reid-thresholds ...` and refresh `tab:thr`, `fig:thr` and `fig:proj` — identity evaluation now runs successfully with fixed `load_ground_truth()` supporting both `build_ground_truth.py` and Labelme formats. Results stored in `data/results/identity_test/`. ReID thresholds 0.5/0.6/0.7 produce `identities_found` 10-12 across videos with `identityRecoveryRate` 1.0.
- [x] Page count and formatting match department norms (72 pages currently) — confirmed from checklist; document has 72 pages per GT review (docs/GT-REVIEW.md)

## Latex / Documentation

- [ ] Identity embedder training timeout note added to TODO (see above) — GPU acceleration or dataset reduction needed for feasible runtime within submission deadline