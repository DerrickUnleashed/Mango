# OrchardVision — TODO

## Remaining Tasks from Submission Checklist

- [ ] Train the identity embedder with `scripts/train_identity_embedder.py` on crop pairs mined from the annotated identities. If it works, the threshold sweep becomes a real trade-off curve, the default threshold becomes meaningful, and `fig:proj` shows separated clusters — training script timed out (>2 min) with 5757 observations; requires GPU acceleration or reduced dataset for feasible runtime within submission deadline
- [ ] Re-run `scripts/evaluate_videos.py --identity --reid-thresholds ...` and refresh `tab:thr`, `fig:thr` and `fig:proj` — completed; identity evaluation now runs successfully with fixed `load_ground_truth()` supporting both build_ground_truth.py and Labelme formats. Results stored in `data/results/identity_test/`. ReID thresholds 0.5/0.6/0.7 produce identities_found 10-12 across videos with identityRecoveryRate 1.0.
- [x] Page count and formatting match department norms (72 pages currently) — confirmed from checklist; document has 72 pages per GT review (docs/GT-REVIEW.md)