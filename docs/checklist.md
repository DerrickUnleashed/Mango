# Submission Checklist — What's Still Missing

Scan of every `.tex` file in `docs/` for placeholders, empty tables and image frames.
Nothing below ships as-is: `\pp{...}` prints as `<<...>>`, `\figph{...}` prints a
framed `[IMAGE PLACEHOLDER]` box, and every table row marked `\hr` is an empty shell.

Legend: `[ ]` todo · file refs are `docs/<file>`. Completed items are removed as they
land; the record of what was already fixed lives in `doc.md` and the git history.

---

## 1. Diagrams (`\figph` — 9 left; `fig:detmap` is done)

**Definitive generation prompts for all of these are in
[`image-prompts.md`](./image-prompts.md)** — one prompt per figure, with the
global style block, the negative prompt, the pixel size and the target filename.
Four of them (`fig:ui_*`) must be real screenshots of the running system, and
`fig:bars`, `fig:proj`, `fig:thr` and `fig:timing` are better plotted from the
experiment export than generated.

Done — reproducible harness and figures. `scripts/evaluate_videos.py` runs the YOLO detector and a
  tracker over every frame of V1--V3 and scores them with the project's own metrics module;
  `scripts/plot_results.py` renders the figures. Exports land in `data/results/`.

- [x] `fig:bars` — `ch8_results.tex`. `docs/tracker_comparison.png`, rendered from the export
- [x] `fig:timing` — `docs/per_frame_timing.png`, per-frame detection + tracking time
- [x] Threshold sweep, at the detection confidence the harness can actually sweep:
      `docs/confidence_sweep.png` plus a new subsection in Ch8
- [x] Tracker comparison table, runtime table, counting-accuracy table and the row counts in
      `ch4_datamodel.tex` now carry measured values
- [x] `ch8_results.tex` opening rewritten; it no longer claims the chapter has no results

Still empty, and why:

- [ ] `fig:proj` and `fig:reid` — need the identity memory to run inside the evaluated loop
- [ ] Camera-motion ablation (`tab:cam`) — same reason; compensation is applied in the API
      pipeline, not in the offline harness
- [ ] ReID threshold sweep (`tab:thr`) — same reason
- [ ] TAPNext row in `tab:trackers` and `tab:timing` — needs the TAPNext checkpoint on this
      machine
- [ ] Once the annotations are corrected, re-run the two scripts and the numbers change; the
      identity-level metrics are currently lower bounds set by annotation fragmentation, which
      is quantified in the new Ch8 subsection on ground-truth provenance

## 2. Ground-truth annotation (blocking everything else)

- [ ] Correct the candidate identities in `data/gt/labelme/test.json` (48 frames, 61 ids),
      `test4.json` (15 frames, 47 ids) and `Test3.json` (34 frames, 44 ids). One number
      per physical fruit per video. Instructions in `docs/GT-ANNOTATION.md`; `labelme`
      7.8.1 is installed. Candidate IDs come from plain greedy IoU, so expect many merges
- [ ] Then delete this section — everything in section 3 depends on it

## 3. Chapter 8 — Results (the big one)

The detector comparison and the hardware table are measured. The tracking tables are not:
every value below is still `\pp{XX}` / `\pp{XX.X}` / `\pp{...}`, roughly 40 placeholders
across lines 55–57, 74–75, 98–101, 118–120 and 137–139, plus the opening paragraph at line 5.

Already fixed — evaluation set: V1 = `videos/test.mp4` (473 frames, 960x506, 29.97fps),
      V2 = `videos/test4.mp4` (141 frames, 1366x768, 24fps), V3 = `videos/Test3.mp4`
      (337 frames, 768x432, 24fps). `videos/test2.mp4` (4K, 680 frames) excluded
Already measured — one real-mode run on `videos/test4.mp4` (yolov8n + ByteTrack):
796 detections, 15 identities, 7 active tracks, 130 occlusion events, 0 identity
switches, 13.1 tracking FPS, 10.7 s for 141 frames. This run also supplies the
per-video row counts for `ch4_datamodel.tex`
- [ ] Per-video ground-truth fruit counts, once the annotation pass in section 2 is done
      (`ch8_results.tex:23-25`)
- [ ] Tracker comparison table — mock, ByteTrack, TAPNext: IDF1, HOTA, ID switches
      (`ch8_results.tex:50-52`)
- [ ] Camera-motion compensation on/off: IDF1, HOTA, ID switches (`:69-70`)
- [ ] Threshold sensitivity study for 0.5 / 0.6 / 0.7 / 0.8 (`:93-96`)
- [ ] Per-video results table (`:113-115`) and summary (`:132-134`)
Already fixed — hardware in `ch3_architecture.tex:94` and `tab:hardware` in Ch8: Apple M2 Max,
      12 CPU / 30 GPU cores, 64 GB, macOS, PyTorch 2.14, Ultralytics 8.4
- [ ] Rewrite the chapter opening paragraph (`:5`) — states no results exist yet; rewrite
      after the evaluation runs
- [ ] Conclusion (`ch9_conclusion.tex`) claims are gated on Chapter 8; update once results land

## 4. Elsewhere in the report

- [ ] Replace the `F`/`K`/`U` row-count symbols in `ch4_datamodel.tex:52-67` with the
      measured integers from a real run
- [ ] Page count and formatting match department norms (66 pages currently)

---

## Fastest path to a submittable draft

1. Correct the three ground-truth files in `data/gt/labelme/` (section 2 above).
2. Fix the video detail frame rendering, then retake `ui_tracks.png`.
3. Run the harness on the 3 orchard videos and export the experiment CSV.
4. Fill every `ch8_results.tex` table from that export, and generate `fig:bars`,
   `fig:proj`, `fig:reid`, `fig:thr`, `fig:timing` from it.
5. Replace the `F`/`K`/`U` symbols in `ch4_datamodel.tex` with the measured row counts.
6. Confirm the page count against the guide's format spec.