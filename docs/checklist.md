# Submission Checklist — What's Still Missing

Scan of every `.tex` file in `docs/` for placeholders, empty tables and image frames.
Nothing below ships as-is: `\pp{...}` prints as `<<...>>`, `\figph{...}` prints a
framed `[IMAGE PLACEHOLDER]` box, and every table row marked `\hr` is an empty shell.

Legend: `[ ]` todo · `[x]` done · file refs are `docs/<file>`.

---

## 1. Front matter (`docs/main.tex`)

- [x] `\guidename` — guide's name (line 136)
- [x] `\guidedesig` — guide's designation (line 137)
- [x] `\hodname` — Head of Department name (line 138)
- [x] `\specname` — specialization name (line 139)
- [x] `\submitdate` — `November, 2026` (line 140)
- [x] Candidate block in order: DERRICK SAMUEL R. (23BCE1040),
      PRANNAVAKHANTH (23BCE1869), PRIYANKA KALIRAJ (23BCE5131) (lines 134–139)
- [x] Declaration + certificate wording reviewed
- [x] Acknowledgement signature line

## 2. Diagrams to draw (`\figph` — 12 total)

Each one replaces a placeholder box with a real figure via `\includegraphics`.

- [ ] `fig:usecase` — `ch3_architecture.tex:95`. UML use-case diagram, 2 actors, 10 use cases
- [ ] `fig:seq` — `ch6_api.tex:78`. Sequence diagram for upload + process + poll
- [ ] `fig:flow` — `ch7_deployment.tex:97`. 7-step user workflow flowchart
- [ ] `fig:frames` — `ch8_results.tex:32`. 3–4 sample orchard frames with boxes drawn
- [ ] `fig:bars` — `ch8_results.tex:59`. Tracker comparison (IDF1 / HOTA / ID switches)
- [ ] `fig:proj` — `ch8_results.tex:79`. t-SNE/PCA of identity prototypes
- [ ] `fig:reid` — `ch8_results.tex:81`. Filmstrip: lost → occluded → reappeared
- [ ] `fig:thr` — `ch8_results.tex:103`. ReID threshold sweep, identities + IDF1
- [ ] `fig:timing` — `ch8_results.tex:141`. Per-frame `proc_ms` over one video
- [ ] `fig:ui_videos` — `ch8_results.tex:147`. Screenshot: video list + upload
- [ ] `fig:ui_tracks` — `ch8_results.tex:149`. Screenshot: track overlay on a frame
- [ ] `fig:ui_exp` — `ch8_results.tex:151`. Screenshot: experiments list + metrics
- [ ] `fig:ui_set` — `ch8_results.tex:153`. Screenshot: pipeline settings page

## 3. Chapter 8 — Results (the big one)

No measured numbers exist yet. Every value below is `\pp{XX}` / `\pp{XX.X}` / `\pp{...}`.

- [ ] Define the evaluation set: videos V1, V2, V3 (what they are, length, fruit count)
- [ ] Per-video ground truth: fruit counts and frame annotations (`ch8_results.tex:23-25`)
- [ ] Row counts per processed video (`ch4_datamodel.tex:77-83`)
      `DetectionRecord`, `FrameTimingRecord`, `Track`, `IdentityRecord`,
      `IdentityObservation`, `ReidEvent`, `CameraMotionRecord`
- [ ] Tracker comparison table — mock, ByteTrack, TAPNext: IDF1, HOTA, ID switches
      (`ch8_results.tex:50-52`)
- [ ] Camera-motion compensation on/off: IDF1, HOTA, ID switches (`:69-70`)
- [ ] Threshold sensitivity study for 0.5 / 0.6 / 0.7 / 0.8 (`:93-96`)
- [ ] Per-video results table (`:113-115`) and summary (`:132-134`)
- [ ] Hardware used for the experiments — CPU/GPU model and RAM (`ch3_architecture.tex:110`)
- [ ] Rewrite the chapter opening paragraph (`:5`) — it currently states no results exist
- [ ] Conclusion (`ch9_conclusion.tex`) claims are gated on Chapter 8; update once results land

## 4. Gantt chart

- [ ] Phase start/end dates in the schedule table (`ch7_deployment.tex:109-114`)
      6 phases: literature survey, data model + API, pipeline + trackers,
      identity learning + analytics, web + experiment harness, testing + report

## 5. Content to write or verify

- [ ] `ch1_introduction.tex` — check scope, objectives (Section 1.5) and contributions
      match what was actually built
- [ ] `ch2_literature.tex` — verify every cited claim against the papers in
      `references.tex`; add any source you consulted but is missing (23 entries exist)
- [ ] `ch5_pipeline.tex` — longest chapter; confirm tracker settings, thresholds and
      stage names match the shipped config
- [ ] `appendices.tex` — repository layout must match the actual tree; add
      API/environment setup instructions if the department expects them
- [ ] `acronyms.tex` — verify each acronym is used at least once in the body
- [ ] `references.tex` — add BibTeX/DOI for anything cited in-text but absent

## 6. Build hygiene

- [x] Highlighting machinery removed (`\hlword`, `\hlgap`, `\hlloop`, `\hlcolor`,
      `\showhl`) — `\add`, `\ph`, `\hr`, `\emphon` now plain pass-throughs (`main.tex:47-56`)
- [x] LaTeX build artifacts gitignored (`*.aux`, `*.fls`, `*.fdb_latexmk`, `*.lof`, `*.lot`, `*.out`, `*.toc`)
- [ ] Final `latexmk -pdf main.tex` clean run — 60 pages, no warnings that matter
- [ ] Page count and formatting match department norms

---

## Fastest path to a submittable draft

1. Fill the four front-matter macros (guide, designation, HOD, specialization).
2. Run the pipeline on 3 orchard videos and export the experiment CSV.
3. Fill every `ch8_results.tex` table from that export; generate the charts from it.
4. Draw the 3 structural diagrams (use-case, sequence, workflow) — the rest are
   screenshots or plots from step 3.
5. Fill Gantt dates, then do a read-through of Chapters 1, 2, 5 against the code.