# Submission Checklist — What's Still Missing

Scan of every `.tex` file in `docs/` for placeholders, empty tables and image frames.
Nothing below ships as-is: `\pp{...}` prints as `<<...>>`, `\figph{...}` prints a
framed `[IMAGE PLACEHOLDER]` box, and every table row marked `\hr` is an empty shell.

Legend: `[ ]` todo · file refs are `docs/<file>`. Completed items are removed as they
land; the record of what was already fixed lives in `doc.md` and the git history.

---

## 1. Diagrams (`\figph` — 9 left)

**Definitive generation prompts for all of these are in
[`image-prompts.md`](./image-prompts.md)** — one prompt per figure, with the
global style block, the negative prompt, the pixel size and the target filename.
Four of them (`fig:ui_*`) must be real screenshots of the running system, and
`fig:bars`, `fig:proj`, `fig:thr` and `fig:timing` are better plotted from the
experiment export than generated.

- [ ] `fig:bars` — `ch8_results.tex:64`. Tracker comparison (IDF1 / HOTA / ID switches)
- [ ] `fig:proj` — `ch8_results.tex:84`. t-SNE/PCA of identity prototypes
- [ ] `fig:reid` — `ch8_results.tex:86`. Filmstrip: lost → occluded → reappeared
- [ ] `fig:thr` — `ch8_results.tex:108`. ReID threshold sweep, identities + IDF1
- [ ] `fig:timing` — `ch8_results.tex:146`. Per-frame `proc_ms` over one video
- [ ] `fig:ui_videos` — `ch8_results.tex:152`. Screenshot: video list + upload
- [ ] `fig:ui_tracks` — `ch8_results.tex:154`. Screenshot: track overlay on a frame
- [ ] `fig:ui_exp` — `ch8_results.tex:156`. Screenshot: experiments list + metrics
- [ ] `fig:ui_set` — `ch8_results.tex:158`. Screenshot: pipeline settings page

## 2. Chapter 8 — Results (the big one)

No measured numbers exist yet. Every value below is `\pp{XX}` / `\pp{XX.X}` / `\pp{...}`:
roughly 40 placeholders across lines 5, 55–57, 74–75, 98–101, 118–120 and 137–139.

- [ ] Define the evaluation set: videos V1, V2, V3 (what they are, length, fruit count)
- [ ] Per-video ground truth: fruit counts and frame annotations (`ch8_results.tex:23-25`)
- [ ] Tracker comparison table — mock, ByteTrack, TAPNext: IDF1, HOTA, ID switches
      (`ch8_results.tex:50-52`)
- [ ] Camera-motion compensation on/off: IDF1, HOTA, ID switches (`:69-70`)
- [ ] Threshold sensitivity study for 0.5 / 0.6 / 0.7 / 0.8 (`:93-96`)
- [ ] Per-video results table (`:113-115`) and summary (`:132-134`)
- [ ] Hardware used for the experiments — CPU/GPU model and RAM
      (`ch3_architecture.tex:95`, still `\pp{CPU / GPU model and memory used for the experiments}`)
- [ ] Rewrite the chapter opening paragraph (`:5`) — states no results exist yet; rewrite
      after the evaluation runs
- [ ] Conclusion (`ch9_conclusion.tex`) claims are gated on Chapter 8; update once results land

## 3. Elsewhere in the report

- [ ] Replace the `F`/`K`/`U` row-count symbols in `ch4_datamodel.tex:52-67` with the
      measured integers from a real run
- [ ] Page count and formatting match department norms (66 pages currently)

---

## Fastest path to a submittable draft

1. Run the pipeline on 3 orchard videos and export the experiment CSV.
2. Fill every `ch8_results.tex` table from that export; generate `fig:bars`, `fig:proj`,
   `fig:reid`, `fig:thr`, `fig:timing` from it and screenshot the four `fig:ui_*` pages.
3. Replace the `F`/`K`/`U` symbols in `ch4_datamodel.tex` with the measured row counts.
4. Fill the experiment-hardware row, then confirm the page count against the guide's
   format spec.