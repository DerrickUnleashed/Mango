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

## 2. Diagrams (`\figph` — 13 total, 7 done, 6 left)

Each one replaces a placeholder box with a real figure via `\includegraphics`.
**Definitive generation prompts for all of these are in
[`image-prompts.md`](./image-prompts.md)** — one prompt per figure, with the
global style block, the negative prompt, the pixel size and the target filename.
Four of them (`fig:ui_*`) must be real screenshots of the running system, and
`fig:bars`, `fig:proj`, `fig:thr` and `fig:timing` are better plotted from the
experiment export than generated.

- [x] `fig:arch` — `ch3_architecture.tex:39`. Architecture diagram (`architecture.png`)
- [x] `fig:usecase` — `ch3_architecture.tex:77`. UML use-case diagram (`usecase.png`)
- [x] `fig:er` — `ch4_datamodel.tex:43`. Data-model ER diagram (`er.png`)
- [x] `fig:seq` — `ch6_api.tex:86`. Sequence diagram for upload + process + poll (`seq.png`)
- [x] `fig:deploy` — `ch7_deployment.tex:32`. Container topology (`deploy.png`)
- [x] `fig:flow` — `ch7_deployment.tex:98`. 7-step user workflow flowchart (`flow.png`)
- [x] `fig:frames` — `ch8_results.tex:34`. Sample orchard frames with boxes (`frames.png`)
- [ ] `fig:bars` — `ch8_results.tex:64`. Tracker comparison (IDF1 / HOTA / ID switches)
- [ ] `fig:proj` — `ch8_results.tex:84`. t-SNE/PCA of identity prototypes
- [ ] `fig:reid` — `ch8_results.tex:86`. Filmstrip: lost → occluded → reappeared
- [ ] `fig:thr` — `ch8_results.tex:108`. ReID threshold sweep, identities + IDF1
- [ ] `fig:timing` — `ch8_results.tex:146`. Per-frame `proc_ms` over one video
- [ ] `fig:ui_videos` — `ch8_results.tex:152`. Screenshot: video list + upload
- [ ] `fig:ui_tracks` — `ch8_results.tex:154`. Screenshot: track overlay on a frame
- [ ] `fig:ui_exp` — `ch8_results.tex:156`. Screenshot: experiments list + metrics
- [ ] `fig:ui_set` — `ch8_results.tex:158`. Screenshot: pipeline settings page

## 3. Chapter 8 — Results (the big one)

No measured numbers exist yet. Every value below is `\pp{XX}` / `\pp{XX.X}` / `\pp{...}`:
roughly 40 placeholders across lines 5, 55–57, 74–75, 98–101, 118–120 and 137–139.

- [ ] Define the evaluation set: videos V1, V2, V3 (what they are, length, fruit count)
- [ ] Per-video ground truth: fruit counts and frame annotations (`ch8_results.tex:23-25`)
- [x] Row counts per processed video (`ch4_datamodel.tex:52-67`) — expressed symbolically
      as `F x d`, `F`, `K`, `U`, `Σ s_i`, `E`, `M` with a symbol legend in the text.
      Swap the symbols for measured integers once a run is available
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

## 4. Gantt chart

- [x] Phase start/end dates in the schedule table (`ch7_deployment.tex:112-119`)
      6 phases, 2026-09-09 to 2026-10-14, derived from the commit history; the text
      notes that the phases overlapped

## 5. Content to write or verify

- [x] `ch1_introduction.tex` — objectives and pipeline description corrected against the code
- [x] `ch2_literature.tex` — every in-text claim checked against its source; each
      author-year citation now carries its reference number. Added 5 sources that were
      used but uncited: InfoNCE [22], DBSCAN [19], t-SNE [21], PCA [20], Ultralytics [23],
      with a paragraph on contrastive training, pseudo-labelling and the 2-D projection.
      Softened the Koirala et al. claim to what the review actually reports. 23 entries
- [x] `ch5_pipeline.tex` — stage names, status models, thresholds, prototype update rule,
      camera-motion modes and the identity-numbering scheme corrected against the code
- [x] `appendices.tex` — repository layout, run commands and sample responses match the
      actual tree, scripts and API
- [x] `acronyms.tex` — all 18 entries now appear in the body. Removed `CRUD`, `S3` and
      `UI`, which were never used (the S3/MinIO deployment claims were removed earlier).
      Introduced `tau_conf`, `tau_match`, `tau_reid` and `alpha` in `ch5_pipeline.tex`
      so every symbol in the nomenclature list is defined where it is used
- [x] `references.tex` — all in-text citations resolve; DOI links can still be added
      for the arXiv-only entries [1], [7], [18] if the department requires them

## 6. Build hygiene

- [x] Highlighting machinery removed (`\hlword`, `\hlgap`, `\hlloop`, `\hlcolor`,
      `\showhl`) — `\add`, `\ph`, `\hr`, `\emphon` now plain pass-throughs (`main.tex:47-56`)
- [x] LaTeX build artifacts gitignored (`*.aux`, `*.fls`, `*.fdb_latexmk`, `*.lof`, `*.lot`, `*.out`, `*.toc`)
- [x] Final `latexmk -pdf main.tex` clean run — 66 pages, exit 0, followed by `latexmk -c`
- [ ] Page count and formatting match department norms (66 pages after the corrections)

---

## Fastest path to a submittable draft

1. Run the pipeline on 3 orchard videos and export the experiment CSV.
2. Fill every `ch8_results.tex` table from that export; generate `fig:bars`, `fig:proj`,
   `fig:reid`, `fig:thr`, `fig:timing` from it and screenshot the four `fig:ui_*` pages.
3. Replace the `F`/`K`/`U` symbols in `ch4_datamodel.tex` with the measured row counts.
4. Fill the experiment-hardware row, then read Chapter 2 against the papers in
   `references.tex`.

---

## Verified against the code (no longer pending)

Content in the chapters that was checked against the repository and corrected:

- API prefix is `/api`, not `/api/v1`; 28 routes listed, including the frame,
  file-streaming and single-track endpoints that were missing (`ch6_api.tex`)
- Job statuses are lowercase (`queued`/`running`/`completed`/`failed`/`cancelled`),
  there are 10 pipeline stages, and progress is a percentage (`ch5`, `ch6`)
- Error envelope is `{"code", "detail", "details"}` — there is no `status` field
- Experiments run synchronously and accept only `mock`/`bytetrack`; TAPNext is
  pipeline-only
- Production uses SQLite + local disk + Redis/Celery, not PostgreSQL/MinIO/S3
  (claims removed from `ch1`, `ch3`, `ch4`, `ch5`, `ch7`, `ch9`)
- Deployment topology figure (`fig:deploy`) redrawn to the real container stack
- Identity numbering is track-chain based with a motion gate, not clustering
- Prototype update, quality gate (0.3), confidence rule (3 obs / 0.5) documented
- Camera-motion estimators are synthetic (`static` / `drift`)
- Per-video analytics does not compute IDF1/HOTA; the evaluation harness does
- Detector/embedder selection in `mock` vs `real` mode documented
- TypeScript types corrected (`VisibilityState` has 5 values, no `ProcessingStatus`)

---

## Last updated

State as of 2026-10-14 on branch `feat/report`: 7 of 13 figures real, Gantt dated,
datamodel row counts symbolic, 66-page PDF building clean. Everything still open lives
in Chapter 8 (measured results) plus the experiment-hardware row and the Chapter 2
citation audit.