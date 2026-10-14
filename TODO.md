# OrchardVision — TODO

## Remaining Tasks from Submission Checklist

- [ ] Train the identity embedder with `scripts/train_identity_embedder.py` on crop pairs mined from the annotated identities. If it works, the threshold sweep becomes a real trade-off curve, the default threshold becomes meaningful, and `fig:proj` shows separated clusters
- [ ] Re-run `scripts/evaluate_videos.py --identity --reid-thresholds ...` and refresh `tab:thr`, `fig:thr` and `fig:proj`