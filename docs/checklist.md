# Submission Checklist — What's Still Missing

Scan of every `.tex` file in `docs/` for placeholders, empty tables and image frames.
`\pp{...}` prints as `<<...>>`, `\figph{...}` prints a framed `[IMAGE PLACEHOLDER]` box, and
every table row marked `\hr` is an empty shell.

Legend: `[ ]` todo · file refs are `docs/<file>`. Completed items are removed as they land;
the record of what was already fixed lives in `doc.md` and the git history.

Current state: no `\pp{...}` placeholders left in Ch8 and one figure placeholder left.
The identity stage now runs inside the offline harness, so `tab:cam`, `tab:thr` and `fig:proj`
are filled with measurements. 72 pages. Ground truth reviewed and signed off
(`docs/GT-REVIEW.md`).

---

## 1. Identity embedder (the one thing that would lift these results)

Both identity results are limited by the same root cause, the appearance embedder is an untrained
ResNet-18. Every candidate similarity lands between 0.90 and 0.96, so the shipped ReID threshold of
0.6 accepts everything and cannot be tuned; the prototype projection shows one loose cloud instead
of clusters.

- [ ] Train the identity embedder with `scripts/train_identity_embedder.py` on crop pairs mined
      from the annotated identities. If it works, the threshold sweep becomes a real trade-off
      curve, the default threshold becomes meaningful, and `fig:proj` shows separated clusters
- [ ] Re-run `scripts/evaluate_videos.py --identity --reid-thresholds ...` and refresh
      `tab:thr`, `fig:thr` and `fig:proj`

## 2. Other open items

- [ ] TAPNext row in `tab:trackers` and `tab:timing` — the checkpoint is not on this machine
- [ ] Page count and formatting match department norms (72 pages currently)

---

## Fastest path to a submittable draft

1. Train the identity embedder (section 2), then re-run the identity sweep and refresh Ch8.
2. Produce `fig:reid` from a clip with a real occlusion gap (section 1).
3. Get the TAPNext checkpoint onto this machine and add its row.
4. Confirm the page count against the guide's format spec.