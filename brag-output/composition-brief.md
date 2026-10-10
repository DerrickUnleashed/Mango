# Hyperframes Composition Brief: OrchardVision

## Objective
Create a short launch-style brag video for OrchardVision — a self-supervised
identity-learning system for tracking and counting mangoes across long orchard
video.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 18.5 seconds

## Source Material
- Project root: `/Users/derricksamuel/Desktop/Projects/Mango`
- Primary files read: `apps/web/src/pages/LandingPage.tsx`,
  `apps/web/src/pages/VideoDetailPage.tsx`, `apps/web/src/pages/VideosPage.tsx`,
  `apps/web/src/pages/DashboardPage.tsx`,
  `apps/web/src/components/tracking/TrackVisualizer.tsx`,
  `apps/web/src/components/tracking/IdentitiesPanel.tsx`,
  `apps/web/src/components/tracking/ReIdPanel.tsx`,
  `apps/web/src/components/tracking/identityColors.ts`,
  `apps/web/src/components/ui/Logo.tsx`, `apps/web/src/index.css`,
  `apps/web/index.html`, `README.md`
- Product name: OrchardVision
- Tagline / strongest claim: "Every mango, counted once."
- Key UI or visual moment to recreate: the claymorphic "Orchard A — North Row"
  live viewport (amber fruit dots with pulse-rings + the four metric chips),
  the upload dropzone + six-stage pipeline, the track overlay with re-id
  recovery, and the Identities panel.
- Copy that must appear verbatim:
  - "Every mango, counted once."
  - "Stop guessing your yield."
  - "Fruit #7 is still Fruit #7." (framing line, ties to the `Fruit #7` label
    already used in the source HeroMock)
  - Pipeline stage names: Detect, Compensate, Track, Remember, Re-identify,
    Evaluate
  - Metric chips: Detected 17 · ID Recovery 0.92 · Count MAE 1.3 · ID Switches 3
  - Re-id row: `track #12 → id-7 · recovered · sim 0.94`
  - "Every fruit gets a persistent identity."
  - "Orchard A — North Row" · "LIVE"

## Creative Direction
- Tone preset: `default`
- Creative direction: dry orchard-instrument product film — precise,
  unbothered, quietly delighted that a mango can never be counted twice.
- Interpretation: comfortable pacing, one idea per scene, amber-on-black
  palette straight from the app. No exclamation marks; the humor sits in the
  deadpan of the situation (a fruit returning to claim its own identity), not
  in gags.
- Angle: follow one identity — **Fruit #7** — from disappearance behind a leaf
  through the pipeline to recovery, landing on "Every mango, counted once."
- Hook: the live orchard viewport where Fruit #7's pulse-ring breaks to `lost`.
- Outro / punchline: "Stop guessing your yield." → OrchardVision logo →
  "Every mango, counted once."
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals (no color washes, no generic particle systems)
  - Unrelated visual redesign — stay in the project's own clay/mango system

## Visual Identity
- Background: `#13161c` (surface-950) / clay canvas `#10131a`
- Text: `#fafafa` (surface-50); secondary `#a1a1aa`
- Accent: mango gradient `#FDE047 → #FBBF24 → #F97316`; orchard-300 `#fcd34d`;
  identity palette `#f59e0b`, `#22d3ee`, `#a78bfa`, `#34d399`, `#fb7185`,
  `#60a5fa`
- Display font: Space Grotesk (fallback: system sans)
- Body font: DM Sans (fallback: system sans)
- Mono font: JetBrains Mono (fallback: ui-monospace)
- Visual references from the project: claymorphic panels (16-24px radii, soft
  double shadow), the mango-mark logo (yellow→orange body + emerald leaf), the
  amber pulse-ring fruit dots, the `Fruit #7` tag, `LIVE` emerald pill, the
  four metric chips, `recovered` / `confident` badges.

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Hook — 3.0s — Orchard viewport; Fruit #7's pulse-ring breaks to `lost`; line "Fruit #7 just disappeared."
2. Reveal — 4.0s — Upload dropzone fills; six pipeline stages arrive in sequence; "Six stages from raw feed to reliable counts."
3. Result — 5.0s — Track overlay recovers Fruit #7; re-id row `track #12 → id-7 · recovered · sim 0.94`; line "Fruit #7 is still Fruit #7."; four metric chips arrive.
4. Highlight — 3.5s — Identities list + embedding map; line "Every fruit gets a persistent identity."
5. Outro — 3.0s — "Stop guessing your yield." → OrchardVision logo + "Every mango, counted once."

## Audio
- Audio role: warm, clean, steady bed with sparse professional accents
- Audio arc: enters steady and warm at the hook; momentum through the pipeline;
  a low swell under the recovery; settles and fades under the final logo bell.
- Music: `assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
  (already copied into the composition)
- Music treatment: start 0, overall volume ~0.32; slight swell (~0.36) under
  Scene 3 recovery; duck to ~0.2 under the final bell; fade out over the last
  ~0.6s.
- Music cue guidance: bundled preset —
  `assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`
  (tempo ~109.96 BPM). Strong cues to target: **8.74s** for the Fruit #7
  recovery reveal, **17.47s** for the logo/outro landing. Use the beat grid
  ~5.3-8.0s for the sequential pipeline-stage reveals. Treat these as hints,
  not a fixed cue sheet.
- Audio-reactive treatment: subtle; use music RMS/bass to make the amber
  orchard glow and the metric chips breathe faintly. No waveform/equalizer
  visuals. If extraction is unavailable, skip it and note it.
- Audio-coupled moments:
  - Scene 1 — soft drop (`impact/impactSoft_medium_*`) as the ring breaks.
  - Scene 2 — light tick per pipeline stage (`interface/click_*` or
    `interface/drop_*`); one click on Start Processing. Low HF-risk, repeated.
  - Scene 3 — warm recovery bell/chime on the #7 re-id snap; quiet ticks on the
    metric chips.
  - Scene 4 — soft tick per identity row.
  - Scene 5 — `impact/impactBell_heavy_000` on the logo landing.
- SFX selection guidance: sparse-moderate. Match the gesture; accent the first,
  last, or strongest items in sequences rather than every item. Prefer low
  HF-risk files for repeated ticks.
- SFX analysis guidance: `/Users/derricksamuel/.config/opencode/skills/brag/assets/sfx/sfx-analysis.md`
- Exact SFX choice: Hyperframes chooses filenames, timestamps, density, and
  volume from the implemented animation.
- Audio files: music is already in
  `brag-output/composition/assets/music/`; copy any selected SFX into
  `brag-output/composition/assets/sfx/{interface,impact}/`.

## Hyperframes Instructions
Load the composition-building Hyperframes domain skills — `hyperframes-core`
(composition contract + `data-*` timing), `hyperframes-animation` (motion),
`hyperframes-creative` (design spec, beats, audio-reactive),
`hyperframes-keyframes` (seek-safe keyframes), and `hyperframes-cli`
(lint/check/render). /brag is its own workflow: do not enter the `hyperframes`
entry-point intent interview and do not route into its generic promo /
launch-video workflow. Prefer native Hyperframes conventions over anything in
`/brag`.

Requirements:
- Show at least one real UI, copy, or visual element from the source project.
- Keep all text readable in the final render.
- Keep the video within 15-25 seconds.
- Include the planned music/SFX layer (audio is enabled for this run).
- Treat `/brag` audio notes as guidance, not a fixed cue sheet. Choose SFX after
  the visual animation exists.
- Treat music cue metadata as optional timing hints. Hyperframes decides exact
  animation timing and should ignore cues that hurt readability, scene pacing,
  or the product story.
- Major reveals may move toward nearby strong cues within about 0.15s. Smaller
  entrances may align to nearby beat points within about 0.10s. Use only 1-3
  strong cue locks in this 18.5s video.
- Use SFX to support motion and interaction: clicks for the simulated process
  action, light ticks for the stage/identity sequences, a recovery chime on
  Fruit #7, and a bell on the final logo.
- Honor the music treatment: low swell under the recovery, duck under the final
  bell, fade out at the end.
- With music present, apply a subtle audio-reactive treatment (glow / panel
  presence driven by RMS/bass). Avoid waveform/equalizer visuals, strobing, or
  text scaling that hurts readability.
- Use local assets for audio and any required runtime/media dependencies when
  possible.
- Run `hyperframes check` before render — it is brag's single gate.
- Keep creation and rendering local. Remote or publishing workflows require a
  separate explicit user request.

## Voiceover
Not enabled.
