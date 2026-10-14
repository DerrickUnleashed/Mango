# Submission Checklist — What's Still Missing

Scan of every `.tex` file in `docs/` for placeholders, empty tables and image frames.
`\pp{...}` prints as `<<...>>`, `\figph{...}` prints a framed `[IMAGE PLACEHOLDER]` box, and
every table row marked `\hr` is an empty shell.

Legend: `[ ]` todo · file refs are `docs/<file>`. Completed items are removed as they land;
the record of what was already fixed lives in `doc.md` and the git history.

Current state: 6 `\pp{...}` values left in Ch8, all inside three tables; 3 figures left,
all gated on the identity memory running inside the evaluated loop.

---

## 1. Ground-truth annotation (blocking)

- [ ] Correct the candidate identities in `data/gt/labelme/test.json` (48 frames, 61 ids),
      `test4.json` (15 frames, 47 ids) and `Test3.json` (34 frames, 44 ids). One number per
      physical fruit per video. Instructions in `docs/GT-ANNOTATION.md`; `labelme` 7.8.1 is
      installed. Candidate ids come from plain greedy IoU, so expect many merges
- [ ] Record the corrected fruit count per video in `ch8_results.tex:23-25` (the dataset table)
- [ ] Re-run `scripts/evaluate_videos.py` and `scripts/plot_results.py`, then update the
      Ch8 numbers. The identity-level metrics are currently lower bounds: the annotations
      split each fruit into about four fragments (41 ids against 10 concurrently visible
      fruit in V1), which is quantified in the Ch8 ground-truth provenance subsection

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
- [ ] Page count and formatting match department norms (66 pages currently)

---

## Already done

- Detector comparison table and validation curves, from the four real training runs in
  `models/*/results.csv`, plus measured inference latency (`ch8_results.tex`, `fig:detmap`)
- Experimental hardware table, and the requirements row in `ch3_architecture.tex`
- Evaluation set fixed: V1 `videos/test.mp4` (473f, 960x506, 29.97fps), V2 `videos/test4.mp4`
  (141f, 1366x768, 24fps), V3 `videos/Test3.mp4` (337f, 768x432, 24fps);
  `videos/test2.mp4` (4K, 680f) excluded
- `fig:bars`, `fig:timing` and a detection-confidence sweep figure, all rendered by
  `scripts/plot_results.py` from the export in `data/results/`
- Tracker comparison, runtime and counting-accuracy tables, and the row counts in
  `ch4_datamodel.tex` (796 / 141 / 7 / 15 / 714 / 0 / 1 from a real run on V2)
- The four `fig:ui_*` screenshots, captured from the running system in `docs/screens/`
- Chapter 8 opening rewritten; it no longer claims the chapter holds no results

---

## Fastest path to a submittable draft

1. Correct the three annotation files in `data/gt/labelme/` (section 1).
2. Re-run `scripts/evaluate_videos.py`, then `scripts/plot_results.py`, and refresh Ch8.
3. Extend the harness to run the identity memory, then fill `tab:cam`, `tab:thr`, `fig:proj`
   and `fig:reid` (section 2).
4. Confirm the page count against the guide's format spec.