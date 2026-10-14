# Submission Checklist — What's Still Missing

Scan of every `.tex` file in `docs/` for placeholders, empty tables and image frames.
`\pp{...}` prints as `<<...>>`, `\figph{...}` prints a framed `[IMAGE PLACEHOLDER]` box, and
every table row marked `\hr` is an empty shell.

Legend: `[ ]` todo · file refs are `docs/<file>`. Completed items are removed as they land;
the record of what was already fixed lives in `doc.md` and the git history.

Current state: 6 `\pp{...}` values left in Ch8, all inside three tables, and 3 figures
left; every one of them is gated on the identity memory running inside the evaluated loop.
72 pages.

---

## 1. Ground-truth review (not blocking any longer)

The identities were selected mechanically, so the long tracks are almost certainly right; the review
below is about the ones the rule dropped. V2's low score is settled: it is a real property of fast
handheld motion, not an artefact of the rule, and it is written up in Ch8.

- [ ] Open the three labelme files in `data/gt/labelme/` and confirm the retained identities.
      Drop any that are not a real fruit, add any that the detector missed


## 2. Harness gaps (need the identity memory in the evaluated loop)

The offline harness scores detection and tracking only. The ReID threshold and the
camera-motion compensation both act inside the identity memory, which the API pipeline runs
but the harness does not, so three tables and two figures cannot honestly be filled yet.

- [ ] `tab:cam` — camera-motion compensation on/off: IDF1, HOTA, ID switches
- [ ] `tab:thr` — ReID threshold sweep at 0.5 / 0.6 / 0.7 / 0.8
- [ ] `fig:proj` — two-dimensional projection of identity prototypes
- [ ] `fig:reid` — filmstrip of a fruit lost and re-identified after an occlusion

## 3. Other open items

- [ ] TAPNext row in `tab:trackers` and `tab:timing` — the checkpoint is not on this machine
- [ ] Page count and formatting match department norms (72 pages currently)

---

## Fastest path to a submittable draft

1. Review the retained identities in `data/gt/labelme/` (section 1), then re-run
   `scripts/evaluate_videos.py` and `scripts/plot_results.py` and refresh Ch8.
2. Extend the harness to run the identity memory, then fill `tab:cam`, `tab:thr`, `fig:proj`
   and `fig:reid` (section 2). This is the only route to the last four gaps.
3. Get the TAPNext checkpoint onto this machine and add its row.
4. Confirm the page count against the guide's format spec.