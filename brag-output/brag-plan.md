# Brag Plan: OrchardVision

## What is this app?
A self-supervised computer-vision system that detects, tracks, and re-identifies
individual mangoes across long pan-tilt-zoom orchard video, so counts stay
correct even when fruit vanish behind leaves, sway in the wind, or leave the
frame.

## The angle
One mango's story. Camera feeds in an orchard are a chaos of occlusion and
drift — fruit appear, disappear, and re-appear. The impressive, specific claim
isn't "we detect mangoes," it's **identity**: a fruit that vanishes behind a
leaf comes back as the *same* fruit, not a new one. So the film follows a
single identity — **Fruit #7** — as it disappears and is recovered, and lands
on the product's own line: "Every mango, counted once." Dry, exact, quietly
delighted. An instrument film, not a hype reel.

## Hook (first 2-3 seconds)
The dark "Orchard A — North Row" live viewport, amber fruit dots breathing with
pulse-rings. One dot is labeled **Fruit #7**. An occlusion sweeps across it:
the ring breaks and flips to amber `lost`. Hard line over it:
**"Fruit #7 just disappeared."** (2.5s) — the disappearing fruit earns the next
20 seconds.

## Key moments (the middle)
- **The pipeline runs.** Six real stages tick by one after another —
  Detect → Compensate → Track → Remember → Re-identify → Evaluate — while the
  upload progress bar fills. The product *doing* it, not describing it.
- **Fruit #7 comes home.** After the gap, the fruit returns from behind the
  leaf and snaps back to the *same* identity color and ID. The real re-id row
  resolves: `track #12 → id-7 · recovered · sim 0.94`.
- **The count is trustworthy.** The real metric chips arrive: `Detected 17`,
  `ID Recovery 0.92`, `Count MAE 1.3`, `ID Switches 3`.

## Outro / punchline
Big type, the product's own CTA: **"Stop guessing your yield."** The
OrchardVision logo (mango mark) slams in with the tagline **"Every mango,
counted once."** Bell rings, music fades under it.

## User flow worth showing
Entry → key action → result, from the actual console pages:
1. **Entry** — the upload dropzone (`VideosPage`): "Drop a video here, or click
   to browse", filename + progress bar fills.
2. **Key action** — start processing (`VideoDetailPage`): the six-stage pipeline
   advances past detection, tracking, identity, re-identification.
3. **Result** — the processed detail page: track overlay on the orchard frame,
   the **Re-identifications** row recovering Fruit #7, the **Identities** list,
   and the four metric chips, all with a stable count.

## Tone
- Preset: `default`
- Creative direction: dry orchard-instrument product film — precise,
  unbothered, quietly delighted that a mango can never be counted twice.
- Interpretation: comfortable pacing, warm amber-on-black palette straight from
  the app, one idea per scene, no exclamation marks. Humor stays in the deadpan
  of the situation (a fruit "claiming" to be itself) rather than jokes.

## Format: landscape — 1920x1080
## Duration: 18.5s

## Visual identity (from the project)
- Background: `#13161c` (surface-950) on clay canvas `#10131a`
- Accent: mango gradient `#FDE047 → #FBBF24 → #F97316`; orchard-300 `#fcd34d`
- Text: `#fafafa` (surface-50)
- Secondary panel text: surface-400 `#a1a1aa`, surface-500 `#94949e`
- Identity palette: `#f59e0b` amber, `#22d3ee` cyan, `#a78bfa` violet,
  `#34d399` emerald, `#fb7185` rose, `#60a5fa` blue
- Display font: Space Grotesk
- Body font: DM Sans
- Mono font: JetBrains Mono
- Strongest visual element: the claymorphic "Orchard A — North Row" viewport —
  amber fruit dots with pulsing rings — and the four metric chips beneath it.

## Share copy (draft)
Every mango, counted once. OrchardVision learns a persistent identity for each
mango, so occlusion, wind, and a swaying camera can't double-count your harvest.

## Audio direction
- Role: warm, clean, steady bed with sparse professional accents — an
  instrument film, precise rather than loud.
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` (1:58, steady
  and clean, ~110 BPM).
- Music treatment: start at 0, volume ~0.32; low swell under the recovery
  payoff; duck slightly under the final logo so the bell rings clear; fade out
  over the last ~0.6s.
- Music cue guidance: bundled preset read —
  `assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`,
  tempo ~109.96 BPM. Target strong cues: **8.74s** (Fruit #7 recovery reveal),
  **17.47s** (logo/outro landing). Beat grid for the six-stage sequential
  reveal near 5.3-8.0s.
- Audio-reactive treatment: subtle; music RMS/bass makes the amber orchard glow
  and the metric chips breathe faintly. No waveform/equalizer visuals.
- SFX posture: sparse-moderate; motion-matched, low HF-risk where repeated.
- Audio-coupled moments: progress-bar fill + pipeline stage ticks; a soft drop
  as the occlusion lands; a recovery chime when Fruit #7 snaps back; a bell on
  the logo. Simulated click on "Start Processing".
- Restraint rule: no SFX on every dot; nothing bright or busy over the orchard
  viewport. The music stays under the copy at all times.

## Storyboard

### Scene 1 — Hook: "Fruit #7 just disappeared." — 3.0s
The dark clay viewport frames "Orchard A — North Row · LIVE". Amber fruit dots
with pulse-rings breathe across it; one carries a `Fruit #7` tag. A soft
occlusion band sweeps across #7; its ring breaks and flips to amber `lost`.
Headline slams in, centered over the lower third: **"Fruit #7 just
disappeared."**
Sequential/interaction: yes — occlusion sweeps across #7 at ~1.4s, ring breaks
and holds.
Audio intent: music enters warm and steady; a soft thud marks the occlusion.
Audio-coupled idea: soft `impact/impactSoft_medium` drop as the ring breaks.
Music: steady clean bed, volume rising to 0.32.
Transition mood: soft crossfade → Scene 2

### Scene 2 — Reveal: the six-stage pipeline — 4.0s
Recreate the upload → process moment from the console. The dropzone shows
`Orchard_north_row.mp4 · up to 2 GB`; a progress bar fills 0→100%. Above it the
six real stage names light up one by one: **Detect · Compensate · Track ·
Remember · Re-identify · Evaluate**. Header: "Six stages from raw feed to
reliable counts."
Sequential/interaction: yes — filename appears, progress fills, six stage chips
arrive in sequence, then the full strip holds (~1.5s settle).
Audio intent: forward momentum; a confident pulse as stages fill.
Audio-coupled idea: subtle ticks per stage (light, low HF-risk), a click on
"Start Processing".
Music: bed continues; stage ticks snap to the beat grid.
Transition mood: clean wipe → Scene 3

### Scene 3 — Result: identity recovery — 5.0s
Centerpiece. The processed orchard frame — track boxes in identity colors over
swaying fruit. Fruit #7's track is lost, then a new detection appears from
behind a leaf and the overlay snaps it to the *same* #7 color and ID. The real
Re-identifications row resolves in mono:
`track #12 → id-7 · recovered · sim 0.94`. Headline: **"Fruit #7 is still
Fruit #7."** Then the four metric chips arrive in sequence: `Detected 17` ·
`ID Recovery 0.92` · `Count MAE 1.3` · `ID Switches 3`, and hold.
Sequential/interaction: yes — track recovery animation, re-id row resolves,
then 4 chips pop in order and hold.
Audio intent: the emotional payoff — relief/confirmation on the recovery.
Audio-coupled idea: recovery chime (warm bell) on the re-id snap; chips tick in
quietly.
Music: bed swells slightly under the recovery.
Transition mood: clean → Scene 4

### Scene 4 — Highlight: persistent identities — 3.5s
The Identities panel: a list of `id-7`, `id-12`, `id-19`, each with its own
identity color dot and a `confident` badge, alongside the embedding map blooming
into clusters. Headline: **"Every fruit gets a persistent identity."** Small
mono footer: "1:1 fruit identity · 0 labeled frames."
Sequential/interaction: yes — identity rows appear one by one; embedding dots
bloom outward.
Audio intent: light, precise, accumulating.
Audio-coupled idea: soft tick per identity row (not every dot).
Music: bed continues.
Transition mood: soft crossfade → Scene 5

### Scene 5 — Outro: the claim — 3.0s
Type slams full-frame: **"Stop guessing your yield."** It holds, then the
mango-mark logo and wordmark **OrchardVision** land with the tagline **"Every
mango, counted once."** Music fades under a final bell; final frames settle to
the logo on the dark canvas.
Sequential/interaction: yes — CTA line, then logo + tagline resolve, hold.
Audio intent: confident, resolved, quiet finish.
Audio-coupled idea: `impact/impactBell_heavy_000` on the logo landing.
Music: duck to ~0.2 for the bell, fade out last 0.6s.
Transition mood: end hold (no cut)

**Music mood for this video:** steady, clean, precise — warm business bed.
**Audio summary:** a warm steady bed carries the film from a fruit's
disappearance through the pipeline and its recovery to a confident, quiet logo
landing, with sparse motion-matched accents and a single bell.

## Voiceover
Not enabled (no `--voice` in the invocation).
