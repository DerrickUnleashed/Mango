# TAPNext++ point tracker — implementation notes

This is the "how it works and why it looks the way it does" document for the
TAPNext++ point-enhanced fruit tracker. Read it before changing anything under
`ml/orchardvision_ml/tracking/tapnext*` or the pipeline frame hook.

## What this is

`TAPNextTracker` is a second short-term tracker behind the same `Tracker`
interface as `MockTracker` and `ByteTrackAdapter`. Where ByteTrack matches
detection boxes with IoU + a Kalman filter, the TAPNext tracker runs Google
DeepMind's **TAPNext++** (Tracking-Any-Point, CVPR 2026) online point model
underneath and matches detections to the model's **predicted points**.

The detector (YOLO) is still the observation source — nothing about detection
changes. The point model's job is *association*: each track owns a query point
at its fruit's centre. Frame by frame the model predicts where that point is
and whether it is visible, so a track "knows" where its fruit is even while
occluded, and re-attaches to the same track id when the fruit reappears near
the predicted point. Output is the standard `TrackResult`
(active tracks, new ids, lost ids, total) so the rest of the pipeline
(embedding, memory, re-identification, evaluation) is untouched.

## Files

| Path | Role |
|---|---|
| `ml/orchardvision_ml/tracking/tapnext/` | **Vendored upstream model code** (byte-faithful, Apache-2.0, from `google-deepmind/tapnet@730cda1c`). Excluded from ruff/mypy/coverage. Do not reformat or refactor. |
| `ml/orchardvision_ml/tracking/tapnext_model.py` | Thin typed wrapper around the vendored `TAPNextPP`: only a `from_checkpoint` override tightening the return type. |
| `ml/orchardvision_ml/tracking/tapnext_tracker.py` | The adapter implementing `Tracker`: seeding, association, buffering, retirement, position-only fallback. **This is where tracker behaviour lives.** |
| `ml/orchardvision_ml/tracking/base.py` | `Tracker` ABC. Gets two new members: `supports_frame_input` and `update_frame(frame)`. |
| `ml/orchardvision_ml/pipeline/real.py` | `CountingPipeline` feeds the current frame to a tracker in `run()` when `tracker.supports_frame_input` is set. |
| `scripts/download_tapnext_weights.py` | Fetches the 256² / 512² checkpoints. |
| `scripts/run_tapnext_tracker.py` | Offline validation run (video → YOLO detections → tracker), no API involved. |
| `ml/tests/test_tapnext.py` | Fake-model tracker tests (no torch) + `RUN_TORCH_TESTS=1` tests against a tiny real TAPNext model. |
| `ml/tests/test_pipeline.py` | Verifies the pipeline calls `update_frame` before `update`. |
| `ml/pyproject.toml` | `tapnext` optional extra; ruff/mypy/coverage excludes for the vendored tree. |

## How a frame flows through the tracker

Per frame, `update(frame_id, detections)` does:

1. **Caches the frame.** The pipeline calls `tracker.update_frame(frame)`
   first (only for trackers with `supports_frame_input=True`); the adapter
   stores it for the model call. Calling `update()` without
   `update_frame()` raises `RuntimeError`.
2. **Classifies detections as new or existing.** A detection is "new" if its
   centre is farther than `match_threshold_px` from every existing track's
   last point (`_near_existing`). New detections create fresh
   `Track`s with a first observation.
3. **Seeds the query set — but only once.** `_advance_model` seeds a query
   point for each new track **only on the first model call** (when `state` is
   `None`), bounded by `max_query_points`. Every later frame steps `state`
   only. See [The fixed query set](#the-fixed-query-set-is-the-core-constraint)
   — this is deliberate.
4. **Associates remaining detections to candidate tracks.** Candidates are
   query tracks whose predicted point is currently *visible*, plus
   position-only tracks (their last known point). `_greedy_match_by_distance`
   pairs detections to candidates by Euclidean distance (winner-take-all,
   ascending order, thresholded). A match appends an observation to the track
   and resets `frames_since_match`.
5. **Handles unmatched detections.** A detection that matches nothing starts
   another new (position-only) track with its box as the last known point.
6. **Ages tracks.** Every track not matched this frame increments
   `frames_since_match` (tracks created *this frame* are exempt — they just
   got an observation). Tracks past `buffer_size` are retired: removed from
   active tracking and reported in `lost_track_ids` (same as ByteTrack).
7. **Reports `TrackResult`.**

Retired tracks deliberately keep their model query row (see next section);
`_query_track_ids` grows monotonically with seeds.

## The fixed query set is the core constraint

TAPNext/TAPNext++ is an "online" model, but with a catch: its recurrent
state (the SSM caches in `tapnext/tapnext_lru_modules.py`) is keyed by **token
position**, and query points are tokens. You can run the model on a *fixed*
query set frame after frame, but you **cannot append query rows mid-stream** —
the old caches no longer line up with the new token count, and the forward
pass fails (verified empirically: an attempt to grow the query set raises a
tensor-shape error, and the upstream torch colab seeds once then only steps
`state`).

Consequences, all by design:

- Query rows are seeded once, on the first model call, from whatever fruit is
  in frame at that moment (up to `max_query_points`, default 256).
- Fruits that appear **later** are still tracked, but **position-only**: their
  last known detection centre is the association point and there is no model
  query behind them. If such a fruit disappears and reappears far away it is
  treated as new (no point model to bridge the gap) — the same degradation
  you would get from a plain box tracker.
- Retired tracks leave their query row in place; the model's token space is
  fixed per stream, so the row is inert but cannot be popped without breaking
  the caches.

Supporting true mid-stream query growth is the TAPNext++ "rebootstrap"
mechanism (replay a bounded window of video with the expanded query set). It
is deferred future work — see [Future work](#future-work).

## Why the pieces sit where they sit

**Vendored model code is byte-faithful.** `tracking/tapnext/*` is copied
verbatim from `google-deepmind/tapnet` (commit `730cda1c`, Apache-2.0) with a
single mechanical edit: absolute imports (`from tapnet.tapnext import …`)
rewritten to relative imports, because the upstream `tapnet` package is not
vendored as a whole. It is excluded from ruff (`extend-exclude`), mypy
(`exclude`), and pytest coverage (`omit`), and it keeps upstream's 2-space
formatting on purpose. Changing it to conform to project style, or "improving"
it, destroys the ability to diff against upstream and ingest bugfixes.

**torch stays lazy.** The CI backend job installs ml without the `tapnext`
extra, so nothing under `orchardvision_ml.tracking` may import torch (or `tapnext_model`)
at package import time. The tracker builds the real model inside
`_ensure_model()` only when a checkpoint is provided; tests inject a fake
model object instead. The `tapnext` extra (`torch`, `torchvision`, `einops`,
`requests`) covers the model stack that `ultralytics` does not guarantee.

**The frame hook is one flag + one method.** `Tracker` gained
`supports_frame_input: bool = False` and a no-op `update_frame(frame)`.
Only trackers that need the raw frame opt in; the pipeline checks the flag
once per frame. This keeps ByteTrack and Mock untouched and makes the contract
explicit rather than hidden in `update()`.

**Association is greedy by distance, not IoU.** Points are cheap to compare
and the model's prediction is the strongest signal we have, so boxes are
compared by predicted-point distance rather than overlap. Adjacent fruits
being close is handled by winner-take-all ordering over ascending distance.

## Configuration reference

| Parameter | Default | Meaning |
|---|---|---|
| `checkpoint_path` | required (or `model=`) | TAPNext++ weights; see download script below. |
| `device` | auto (cuda → cpu) | Torch device; ignored when a model is injected. |
| `input_resolution` | `256` | Must match the checkpoint: `256` (`tapnextpp_ckpt.pt`) or `512` (`tapnextpp_512.ckpt`). |
| `model` | `None` | Pre-built object with a `track_frame(frame_bgr, query_points_xy=None, state=None) -> (positions_xy, visible, state)`. Tests and embedding hosts. |
| `match_threshold_px` | `120.0` | Display-pixel radius deciding "new detection" and association matching. Larger = more merge-y, smaller = more fragmentation. |
| `buffer_size` | `30` | Frames a track is kept after its last match before being reported lost. |
| `max_query_points` | `256` | Cap on the *initial* query set (model point capacity). |

## Running it

```bash
# one-time: install the model stack + fetch weights (~170 MB)
uv sync --project ml --extra tapnext
python scripts/download_tapnext_weights.py              # -> models/tapnextpp_ckpt.pt
python scripts/download_tapnext_weights.py --resolution 512

# offline validation (no API): video -> YOLO detections -> tracker
python scripts/run_tapnext_tracker.py data/videos/orchard.mp4 \
    --checkpoint models/tapnextpp_ckpt.pt --model-path models/yolov8n.pt \
    --max-frames 300

# tests
RUN_TORCH_TESTS=1 uv run --project ml pytest ml/tests -q
```

## Future work / how to change it

- **Mid-stream queries (rebootstrap).** To grow the query set while a stream
  is live you must re-seed the model from a stored checkpoint frame and replay
  the buffered frames with the expanded query set. Sketch: keep a ring buffer
  of recent frames in the tracker; when a new fruit needs a query and the
  buffer is non-empty, restart `state` at the buffer head with all live +
  pending queries and replay forward. Expect a compute burst proportional to
  the replay length; the upstream colab's online loop is the behavioural
  reference.
- **API wiring.** `apps/api` currently validates `tracker` against
  `^(mock|bytetrack)$` and constructs the tracker in `video.py`/`processing.py`.
  Adding `tapnext` means: extend the schema/regex, build the tracker from the
  persisted checkpoint path (and remember `apps/api` runs torch-less — the
  tracker must stay lazy there too), and surface `matchThresholdPx` /
  `bufferSize` through `GET/PUT /api/settings`.
- **Tuning.** `match_threshold_px` dominates behaviour. Fruits in tight canopy
  may need a smaller radius to avoid merges; fast-moving fruit may need a
  larger one. `buffer_size` trades lost-reports vs stale tracks and is worth
  aligning with the occlusion-tolerance of the re-identification step.
- **512 checkpoints.** Pass `--resolution 512` to the download script and set
  `input_resolution=512`; the wrapper interpolates the position encoding. Cost
  per frame grows like resolution².
- **Fake-model contract.** Any injected model must speak
  `track_frame(frame, query_points_xy=None, state=None) -> (positions_xy,
  visible, state)` with rows ordered exactly like the query set, because
  `_advance_model` indexes predictions by query index.

## Known limitations

- No mid-stream query growth (see above) — late-entering fruit is position-only.
- Query rows are permanent for a stream; long-running streams with many
  entrants never claim a query for the late ones without a rebootstrap.
- Untrained/random weights produce arbitrary positions and visibility, so
  behavioural integration tests keep to structural invariants (query set size,
  track counts) rather than exact positions.
- Per-frame cost is the TAPNext++ forward (ms-scale on GPU, slower on CPU);
  the tracker is aimed at the GPU runtime, not the default dev loop.