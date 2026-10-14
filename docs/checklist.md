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

Ground truth is now built by `scripts/build_ground_truth.py`: full-frame-rate association plus a
minimum-track-length rule of 50 frames. V1 61 raw ids -> 9 kept, V2 44 -> 7, V3 43 -> 14, all
consistent with the 10/10/12 concurrency bound. IDF1 on this ground truth is 0.87-0.97 for V1
and V3 and 0.23-0.27 for V2.

- [ ] Open the three labelme files in `data/gt/labelme/` and confirm the retained identities.
      Drop any that are not a real fruit, add any that the detector missed. The rule was
      mechanical, so the long tracks are almost certainly right and the interesting check is
      whether a real fruit was dropped for being short
Two limits are stated in the Ch8 ground-truth subsection rather than left implicit: the ground truth comes
from the same detector the system runs, so the identity metrics measure identity consistency and not
detector accuracy; and it has not been confirmed by a person.

- [ ] Decide whether V2's low score (0.23) is a real property of fast handheld motion on a 141-frame
      clip, or an artefact of the same 50-frame rule discarding short tracks. This is the one number
      in Ch8 that most needs a second opinion

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

## Already done

- Detector comparison table and validation curves, from the four real training runs in
  `models/*/results.csv`, plus measured inference latency (`ch8_results.tex`, `fig:detmap`)
- Experimental hardware table, and the requirements row in `ch3_architecture.tex`
- Evaluation set fixed: V1 `videos/test.mp4` (473f, 960x506, 29.97fps), V2 `videos/test4.mp4`
  (141f, 1366x768, 24fps), V3 `videos/Test3.mp4` (337f, 768x432, 24fps);
  `videos/test2.mp4` (4K, 680f) excluded
- `fig:bars`, `fig:timing` and a detection-confidence sweep figure, all rendered by
  `scripts/plot_results.py` from the export in `data/results/`
- Ground truth built by `scripts/build_ground_truth.py`: full-frame-rate association plus a 50-frame
  minimum track length. V1 61 raw ids -> 9 kept, V2 44 -> 7, V3 43 -> 14, each consistent with the
  10 / 10 / 12 max-concurrent bound
- Tracker comparison, runtime and counting-accuracy tables filled from the rebuilt ground truth:
  IDF1 70.9 (mock) and 69.0 (ByteTrack) averaged over V1--V3, count MAE 0.67 and 0.61
- Row counts in `ch4_datamodel.tex` (796 / 141 / 7 / 15 / 714 / 0 / 1 from a real run on V2)
- The four `fig:ui_*` screenshots, captured from the running system in `docs/screens/`
- Chapter 8 opening rewritten; it no longer claims the chapter holds no results

---

## Fastest path to a submittable draft

1. Review the retained identities in `data/gt/labelme/` (section 1), then re-run
   `scripts/evaluate_videos.py` and `scripts/plot_results.py` and refresh Ch8.
2. Extend the harness to run the identity memory, then fill `tab:cam`, `tab:thr`, `fig:proj`
   and `fig:reid` (section 2). This is the only route to the last four gaps.
3. Get the TAPNext checkpoint onto this machine and add its row.
4. Confirm the page count against the guide's format spec.