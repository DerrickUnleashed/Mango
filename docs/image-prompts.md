# Image Prompts for the Report Placeholders

Twelve figures are still `[IMAGE PLACEHOLDER]` boxes. Each entry below gives a
**definitive prompt** you can paste into an image generator, plus the technical
specs (size, format, file name) for dropping the result into `docs/` and
replacing the `\figph{...}` call with `\includegraphics`.

## Global style rules (apply to every image)

Use this block as a prefix on all prompts unless noted:

> Technical documentation figure, flat vector illustration, clean line art, white
> background, no photographic texture, no gradients, no drop shadows, no 3D
> perspective, no hand-drawn sketchiness. Palette: deep green `#1F6F43`, warm
> mango orange `#E8873A`, slate grey `#475569`, light grey `#E2E8F0`, white
> `#FFFFFF`. Stroke weight 2px, corner radius 8px, Arial/Helvetica labels,
> label size no smaller than 18px at final size. Everything must stay legible
> when scaled to 12 cm width in a printed A4 document.

**Universal negative prompt:**

> photorealistic, 3d render, watermark, signature, blurry, low resolution, jpeg
> artifacts, cluttered background, gradient mesh, neon colours, illegible text,
> misspelled text, distorted letters, extra limbs, stock-photo watermark

Text in generated diagrams is the weakest part of every image model. Two rules:

1. Ask for **labelled shapes**, then check the spelling before use.
2. If labels come out garbled, generate the artwork without text and add the
   labels in a vector editor — or, better, redraw these three figures directly
   in TikZ, which is already a dependency of `main.tex` (`fig:usecase`,
   `fig:seq`, `fig:flow`). The nine data/screenshot figures are better taken
   from real runs than generated at all.

## Sizes and formats

| Figure | LaTeX width | Recommended render | Format |
|---|---|---|---|
| `fig:usecase` | 14 cm | 2100×900 px | PNG (line art) |
| `fig:seq` | 14 cm | 2100×1050 px | PNG |
| `fig:flow` | 14 cm | 2100×700 px | PNG |
| `fig:frames` | 14 cm | 2400×700 px | PNG or JPEG |
| `fig:bars` | 14 cm | 2000×800 px | PNG |
| `fig:proj` | 14 cm | 1600×1200 px | PNG |
| `fig:reid` | 14 cm | 2400×700 px | PNG |
| `fig:thr` | 14 cm | 1800×1000 px | PNG |
| `fig:timing` | 14 cm | 2000×800 px | PNG |
| `fig:ui_*` (4) | 14 cm | 1600×1000 px | PNG |

Always export PNG for line art (lossless, crisp text) and JPEG (quality 90) for
photographic frames. Name files `fig-<name>.png` and put them in `docs/figures/`.

---

## 1. `fig:usecase` — Use-case diagram (ch3_architecture.tex:95)

> A UML use-case diagram for a computer-vision web application. On the left, two
> stick-figure actors labelled "Analyst" and "Experimenter", with Experimenter
> placed slightly below and to the right of Analyst and connected to Analyst by
> a solid line labelled "inherits". In the centre, a large rounded rectangle
> labelled "OrchardVision" containing ten vertical ellipses arranged in two
> columns of five, labelled: "Upload video", "Process video", "View tracks",
> "View identities", "View identity projection", "View ReID events", "View
> analytics", "Manage experiments", "Export results", "Edit settings", "Delete
> video". Connect each actor to the ellipses it uses with plain solid lines.
> Draw a dashed arrow labelled "«include»" from "Process video" to "Upload
> video". Draw a dashed arrow labelled "«extend»" from "Export results" to
> "Manage experiments". No use case may be connected to more than three
> ellipses.

## 2. `fig:seq` — Sequence diagram of a processing request (ch6_api.tex:78)

> A UML sequence diagram with six vertical lifelines labelled left to right:
> "Client", "FastAPI router", "StorageService", "Database", "Worker", "Pipeline".
> Each lifeline is a thin dashed vertical line with a small header box. Draw
> horizontal arrows with open arrowheads, each with a label above it, in this
> exact order: 1. Client to FastAPI router, "POST /videos (multipart)". 2. FastAPI
> router to StorageService, "save_upload()". 3. StorageService to FastAPI router,
> "path". 4. FastAPI router to Database, "INSERT Video (status=uploaded)". 5.
> Client to FastAPI router, "POST /videos/{id}/process". 6. FastAPI router to
> Database, "INSERT ProcessingJob (queued)". 7. FastAPI router to Worker, "enqueue
> task". 8. Worker to Pipeline, "run_processing_sync()". 9. Pipeline to Database,
> "UPDATE stage, progress" repeated four times, each with a different stage
> label: "extracting_frames / detecting", "tracking", "embedding, memory, reid",
> "analytics". 10. Pipeline to Database, "UPDATE Video (status=processed)". 11.
> Client to FastAPI router, "GET /jobs/{id} (poll)", with a dashed arrow
> returning "stage, progress". Keep every arrow horizontal and evenly spaced.

## 3. `fig:flow` — User workflow flowchart (ch7_deployment.tex:97)

> A horizontal flowchart of seven rounded rectangles connected left to right by
> straight arrows, labelled in order: "Start services", "Review settings",
> "Upload video", "Start processing", "Inspect results", "Run experiment",
> "Clean up". Below the fourth box add a small sub-box "Stage and progress bar".
> Draw one dashed curved arrow looping from "Inspect results" back up to
> "Review settings", labelled "adjust thresholds". Draw one dashed curved arrow
> from "Clean up" back to "Upload video", labelled "next video". The overall
> arrangement is a gentle left-to-right flow that wraps to a second row, with
> generous whitespace and no other decoration.

## 4. `fig:frames` — Sample orchard frames (ch8_results.tex:32)

> Four photographic frames in a single horizontal row, taken from mango orchard
> video. Each frame is the same camera view with slight differences: frame 1
> shows evenly lit green mangoes clearly visible between leaves; frame 2 shows
> the same canopy with harsh sunlight and hard shadows, some fruit blown out to
> white; frame 3 shows a dense cluster of leaves covering most of the fruit, only
> partial orange-yellow mangoes peeking through; frame 4 shows fruit partially
> hidden behind a branch with deep shadow. Each frame has a thin white
> bounding box drawn around one clearly visible mango with a small label
> "0.91", "0.87", "0.62", "0.44" in its top-left corner. Realistic outdoor
> daylight photography, natural green foliage, mango fruit in greens, yellows and
> reds, shallow depth of field, no people, no text overlays other than the
> confidence labels.

**Do not generate this one if you have real orchard frames** — real frames from
your own evaluation videos are both more honest and more useful.

## 5. `fig:bars` — Tracker comparison chart (ch8_results.tex:59)

> A grouped bar chart on a white background comparing three trackers on the
> horizontal axis: "mock", "ByteTrack", "TAPNext". The left vertical axis is
> labelled "IDF1 / HOTA (%)" and runs from 0 to 100 with ticks every 20. Each
> tracker has two adjacent bars: a solid deep-green bar for IDF1 and a solid
> mango-orange bar for HOTA. Overlaid on the same chart, a line with circular
> markers in slate grey, using the right vertical axis labelled "ID switches"
> running from 0 to 60, connects the three ID-switch values, one marker per
> tracker, with a light grey horizontal grid behind everything. Include a
> compact legend in the top-right corner with the three entries "IDF1", "HOTA",
> "ID switches". Axis titles and legend text in dark grey, no chart title, no
> 3D effect, no gradient fills.

Better: export this directly from `GET /experiments/{id}/export` and plot it in
Python or a spreadsheet. Numbers from a fabricated chart are the one thing that
must never happen in this report.

## 6. `fig:proj` — Identity embedding projection (ch8_results.tex:79)

> A scatter plot on a light grey plotting area with a 5×5 grid of thin grey
> lines. Roughly 60 circular markers of varying size are scattered in nine
> clearly separated clusters. Most markers are deep green and semi-transparent;
> twelve markers are mango orange to represent identities flagged as not yet
> confident. Marker radius varies with the number of observations, from small to
> large. Two clusters are connected by a dashed mango-orange arrow annotated
> "re-identified after occlusion". Include axes labelled "t-SNE 1" and "t-SNE 2"
> with numeric ticks from −40 to 40. No chart title, no legend box, no colourbar.

Better generated from `GET /videos/{id}/identities/projection` with matplotlib.

## 7. `fig:reid` — Re-identification example (ch8_results.tex:81)

> A horizontal filmstrip of four photographic crops from the same mango orchard
> video, all showing the same single mango fruit at increasing frame numbers,
> each crop 420×420 pixels and separated by a thin white gutter. Crop 1: the
> mango fully visible, a solid deep-green bounding box around it labelled "#7".
> Crop 2: the mango almost entirely hidden behind a large green leaf, only a
> sliver of yellow visible, the box drawn as a dashed amber rectangle labelled
> "#7 lost". Crop 3: the mango visible again, solid deep-green bounding box
> labelled "#7 recovered", with a small green check mark above the box. Crop 4:
> the same mango in a later position in the frame, solid deep-green bounding box
> labelled "#7". Small frame numbers "412", "430", "466", "500" below each crop.
> Photographic, natural daylight, consistent colour and scale across all four
> crops.

## 8. `fig:thr` — Threshold sweep (ch8_results.tex:103)

> A line chart with the horizontal axis labelled "ReID threshold" running from
> 0.50 to 0.80 with ticks at 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80. The left
> vertical axis is labelled "Identities found" from 0 to 120 with ticks every
> 20, drawn as a solid deep-green line with circular markers that decreases
> monotonically as the threshold rises. A second dashed mango-orange line uses
> the right vertical axis labelled "IDF1 (%)" from 0 to 100 and rises then falls,
peaking near threshold 0.65. A horizontal grey dashed reference line across
> the plot at the value matching the ground-truth fruit count, labelled "ground
> truth = 47". A single mango-orange filled circle marks the chosen operating
> point at threshold 0.60, with a small annotation "selected". Light grey grid,
> no title, no 3D.

## 9. `fig:timing` — Per-frame processing time (ch8_results.tex:141)

> A line chart with the horizontal axis labelled "Frame index" from 0 to 310 and
> the vertical axis labelled "Processing time (ms)" from 0 to 180. Two lines: a
> solid deep-green line for the "ByteTrack" configuration and a dashed
> mango-orange line for the "mock" configuration. Both lines are noisy at small
> scale and both show one clear spike near frame 20 to about 160 ms, annotated
> with a small text label "model warm-up". A compact legend in the top-right
> corner with entries "ByteTrack" and "mock". Light grey grid, no title, no 3D.

## 10. `fig:ui_videos` — Video list and upload screen (ch8_results.tex:147)

> A clean web application screenshot of a video management page. Left sidebar
> with a small logo at the top and a vertical navigation list: "Dashboard",
> "Videos" (highlighted as the active item), "Identities", "Re-identification",
> "Evaluation", "Analytics", "Settings". Main area: a page heading "Videos" and
> below it a dashed-border drag-and-drop upload zone with a cloud-upload icon and
> the text "Drop a video here or click to browse". Underneath, a grid of three
> video cards; each card shows a thumbnail of an orchard frame, a filename
> "row_03.mp4", a resolution line "1920×1080 · 30 fps", and a coloured status
> pill reading "processed", "processing" and "uploaded" respectively. Neutral
> light background, white cards, soft rounded corners, restrained green accent
> colour, sans-serif UI font. No browser chrome, no cursor, no real person's
> name.

This and the next three must be real screenshots of the running application.
Generate them only as a fallback if the system is not running.

## 11. `fig:ui_tracks` — Track visualisation (ch8_results.tex:149)

> A screenshot of a video analysis interface. Left two-thirds: a video frame of
> a mango orchard with coloured tracking overlays drawn on it — six mango
> bounding boxes in distinct colours (green, orange, blue, purple, teal, red),
> each with a small label "#1" to "#6" above the box, and thin coloured polyline
> trails following each fruit's path across the frame. One box is drawn as a
> dashed amber rectangle with an amber translucent fill, labelled "#3 occluded".
> Right third: a panel titled "Identities" listing rows with a colour swatch,
> the identity number, an observation count and a quality bar. Bottom: a video
> scrubber with a frame slider and a play button, and a small chip labelled
> "Detections" in the bottom-right corner of the video area. Light application
> chrome matching a modern analytics dashboard, sans-serif UI font.

## 12. `fig:ui_exp` — Experiment management screen (ch8_results.tex:151)

> A screenshot of an experiment evaluation page. Left sidebar navigation as in
> the video page but with "Evaluation" highlighted. Main area: heading
> "Experiments" and a small form with two labelled controls, a "Tracker"
> dropdown showing "ByteTrack" and a "Frames" number input showing "310", plus a
> solid green "Run experiment" button. Below, a data table with the column
> headers "Name", "Tracker", "Frames", "Status", "IDF1", "HOTA", "ID switches",
> "Count MAE". Four rows: two with a green "completed" status pill and numeric
> metric values, one with an amber "running" pill and dashes in the metric
> columns, one with a grey "failed" pill. To the right of each completed row,
> two small icon buttons labelled "JSON" and "CSV". White background, light grey
> table row separators, restrained green accents, sans-serif UI font.

## 13. `fig:ui_set` — Settings screen (ch8_results.tex:153)

> A screenshot of a pipeline settings page, single-column form. Left sidebar
> navigation with "Settings" highlighted. Main area: heading "Pipeline settings"
> and six grouped sections separated by thin dividers, each with a bold section
> label and labelled numeric inputs with small stepper buttons: "Detector" with
> "Confidence threshold 0.35"; "Tracker" with "Match threshold (px) 120" and
> "Buffer frames 30"; "Re-identification" with "ReID threshold 0.60" and
> "Occlusion timeout (s) 30"; "Identity memory" with "Memory update rate 0.20";
> "Camera motion" with two radio buttons "Static" (selected) and "Drift";
> "Visualization" with five checkboxes, all ticked, labelled "Track visualizer",
> "Identities panel", "Re-ID panel", "Motion panel", "Analytics panel". A solid
> green "Save settings" button at the bottom right and a small grey text line
> "Revision 4 · updated 2 hours ago" below it. White background, sans-serif UI
> font, restrained green accents.

---

## Wiring an image into the report

Replace the placeholder call with a figure of the same size, keeping the label:

```latex
\begin{figure}[htbp]
\centering
\includegraphics[width=0.92\linewidth]{figures/fig-bars.png}
\caption{Tracker comparison on the evaluation set.}
\label{fig:bars}
\end{figure}
```

The labels (`fig:usecase`, `fig:seq`, `fig:flow`, `fig:frames`, `fig:bars`,
`fig:proj`, `fig:reid`, `fig:thr`, `fig:timing`, `fig:ui_videos`,
`fig:ui_tracks`, `fig:ui_exp`, `fig:ui_set`) are already referenced by the text,
so keep them exactly. After editing, rebuild with `latexmk -pdf main.tex` and
confirm the list of figures and the page count.