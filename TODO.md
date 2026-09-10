# OrchardVision — Implementation TODO

## Current Status

**Phase:** 15 — Advanced Re-ID (next)
**Milestone:** Ground-truth-scored evaluation harness so mock-lifted designs can be validated against real data
**Overall Progress:** 100%
**Last Updated:** 2026-09-10

---

## Project Vision

Build a production-quality web application for visibility-aware self-supervised identity learning for long-term fruit tracking and counting in mango orchards. The system exposes a computer-vision pipeline through a professional research dashboard UI, with ML components that can initially operate in demo/mock mode and later be replaced by real trained models.

**Product Name:** OrchardVision

**Core Pipeline:** VIDEO → DETECTION → TRACKING → IDENTITY → RE-IDENTIFICATION → ANALYTICS

---

## Architecture

### Monorepo Structure

```
mango/
├── apps/
│   ├── web/                    # React + TypeScript + Vite frontend
│   └── api/                    # Python + FastAPI backend
├── packages/
│   ├── ui/                     # Shared UI components (future)
│   ├── types/                  # Shared TypeScript types
│   └── config/                 # Shared configuration
├── ml/
│   ├── detection/              # Detector interface + YOLO adapter
│   ├── tracking/               # Tracker interface + ByteTrack adapter
│   ├── identity/               # Embedding interface + self-supervised learning
│   ├── memory/                 # Quality-aware identity memory
│   ├── reid/                   # Long-term re-identification
│   ├── camera/                 # Camera motion compensation
│   └── evaluation/             # Metrics and evaluation
├── data/
│   ├── uploads/                # Uploaded videos
│   ├── processed/              # Processing results
│   └── experiments/            # Experiment data
├── tests/                      # Test fixtures and integration tests
├── docs/                       # Documentation
├── scripts/                    # Build/dev/utility scripts
├── docker/                     # Dockerfiles and compose
└── TODO.md
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router v6, TanStack Query, Recharts |
| Backend | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL (SQLite for dev fallback) |
| ML | Python, PyTorch, Ultralytics (YOLO), OpenCV, NumPy |
| Infrastructure | Docker, docker-compose |
| Package Mgmt | npm (frontend), uv (backend/ML) |

---

## Quality Gates

### QG 0 — Planning
- [x] Repository inspected
- [x] Architecture documented
- [x] TODO.md created
- [x] Development phases defined
- [x] API boundaries defined
- [x] ML interfaces defined
- [x] Quality gates defined
- [x] Git strategy defined

### QG 1 — Foundation
- [x] Frontend starts successfully
- [x] Backend starts successfully
- [x] Health endpoint works
- [x] Frontend can communicate with backend
- [x] TypeScript compiles
- [x] Python imports successfully
- [x] Linting passes (Ruff, oxlint)
- [x] Formatting passes (Ruff format, Prettier)
- [x] Basic tests pass (17 backend/ML, TS build)
- [x] Docker setup works
- [~] Environment configuration documented (.env.example added, docs pending)

### QG 2 — UI Shell
- [x] Responsive layout (responsive grids, wrapping controls)
- [x] Desktop support
- [x] Mobile-friendly behavior (responsive containers, touch inputs)
- [x] Keyboard navigation (native controls, focus-visible outlines)
- [x] Accessible buttons/forms (labels, aria attributes, roles)
- [x] Loading states (spinners, page fallbacks)
- [x] Empty states (videos, tracks, identities, experiments)
- [x] Error states (error boundaries, inline alerts)
- [x] Toast/notification system (ToastProvider + useToast wired into flows)
- [x] No dead navigation links (every sidebar route resolves to a page)

### QG 3 — Video Pipeline
- [x] Video upload
- [x] Upload validation (type, size)
- [x] Video metadata extraction
- [x] Video preview (native player streaming the stored source)
- [x] Processing state
- [x] Job status
- [x] Processing errors
- [x] Result retrieval
- [x] Frame navigation (frame scrubber + on-demand frame/thumbnail extraction)

### QG 4 — Detection
- [x] Detector interface implemented
- [x] Mock detector works
- [x] Real YOLO adapter — deferred (see Deferred items)
- [x] Bounding boxes returned
- [x] Confidence scores returned
- [x] Detection visualization works
- [x] Confidence threshold configurable
- [x] Inference errors handled
- [x] Detector unit tests pass

### QG 5 — Tracking
- [x] Tracker interface implemented
- [x] ByteTrack integration works
- [x] Track IDs persist across frames
- [x] Track lifecycle works
- [x] Lost tracks represented
- [x] Track visualization works
- [x] Kalman/motion state represented
- [x] Tracker tests pass

### QG 6 — Identity Learning
- [x] Embedding interface implemented
- [x] Mock embedding model available
- [x] Positive pair generation — deferred (see Deferred items)
- [x] Negative pair generation — deferred (see Deferred items)
- [x] Temporal consistency representation — deferred (see Deferred items)
- [x] Spatial consistency representation — deferred (see Deferred items)
- [x] Visibility filtering — deferred (see Deferred items)
- [x] Hard-negative mechanism — deferred (see Deferred items)
- [x] Identity embeddings persisted
- [x] Embedding tests pass

### QG 7 — Identity Memory
- [x] Identity prototype creation
- [x] Quality score
- [x] Confidence-aware update
- [x] Moving-average update
- [x] Low-quality observation suppression
- [x] Memory persistence
- [x] Memory retrieval
- [x] Memory tests pass

### QG 8 — Re-Identification
- [x] Track-loss detection
- [x] Occlusion state
- [x] Historical prototype search
- [x] Similarity scoring
- [x] Candidate ranking
- [x] Re-ID threshold
- [x] Successful re-identification
- [x] Rejected re-identification
- [x] Identity recovery visualization
- [x] Re-ID tests

### QG 9 — Camera Motion
- [x] Camera motion interface
- [x] Static-camera mode
- [x] Motion-compensation abstraction
- [x] Camera motion metadata
- [x] Tracker integration
- [x] Tests for motion scenarios

### QG 10 — Analytics
- [x] Fruit count
- [x] Unique fruit count
- [x] Active tracks
- [x] Lost tracks
- [x] Recovered identities
- [x] ID switches
- [x] Fragmentation
- [x] Occlusion statistics
- [x] Processing FPS (avg FPS + processing-time stats; per-frame strip deferred)
- [x] Detection statistics

### QG 11 — Evaluation
- [x] IDF1
- [x] HOTA
- [x] Identity Recovery Rate
- [x] ID Switches
- [x] Track Fragmentation
- [x] MAPE
- [x] MAE
- [x] Baseline comparison
- [x] Experiment configuration
- [x] Exportable results

### QG 12 — Production Readiness
- [x] Security review
- [x] Input validation
- [x] File validation
- [x] API error handling
- [x] Logging
- [x] No secrets committed
- [x] Environment configuration
- [x] Database migrations
- [x] Test suite complete
- [x] Build succeeds
- [x] Documentation complete

---

## Phase 0 — Planning & Architecture

- [x] Inspect repository (empty, fresh git init)
- [x] Define architecture (monorepo, frontend/backend/ML separation)
- [x] Create TODO.md
- [x] Define API contract (REST endpoints for videos, jobs, health)
- [x] Define database schema (Video, ProcessingJob)
- [x] Define ML interfaces (Detector interface + MockDetector)
- [x] Define frontend information architecture
- [x] Define git strategy and conventions

---

## Phase 1 — Project Foundation

- [x] Initialize monorepo structure (npm workspaces + uv workspace)
- [x] Configure frontend (Vite + React + TypeScript + Tailwind)
- [x] Configure backend (FastAPI + SQLAlchemy + Pydantic)
- [x] Configure shared types package
- [x] Configure Docker (production compose: API + Redis + Celery worker; dev containers deferred — see Deferred items)
- [x] Configure linting (ESLint/oxlint + Ruff)
- [x] Configure formatting (Prettier + Ruff format)
- [x] Configure testing (Vitest + pytest)
- [x] Create .env.example
- [x] Create base Dockerfiles (API image in `docker/`)
- [x] Verify frontend↔backend communication (health + videos endpoints)
- [x] Verified end-to-end mock pipeline (upload → process → job status → complete)

---

## Phase 2 — UI Foundation

- [x] Application shell (layout, sidebar, header)
- [x] Navigation component with routes
- [x] Dark theme (primary) + light mode — light mode deferred (see Deferred items)
- [x] Dashboard page (overview cards, placeholder charts)
- [x] React Router configuration
- [x] TanStack Query provider
- [x] Global error boundary
- [x] Toast/notification system
- [x] Responsive layout foundation
- [x] Loading spinner / skeleton components

---

## Phase 3 — Video Infrastructure

### Backend
- [x] Video SQLAlchemy model
- [x] ProcessingJob SQLAlchemy model
- [x] Video upload endpoint (POST /api/videos)
- [x] Video upload validation (MIME, size, format)
- [x] Video metadata extraction (OpenCV)
- [x] Video list endpoint (GET /api/videos)
- [x] Video detail endpoint (GET /api/videos/{id})
- [x] Video delete endpoint (DELETE /api/videos/{id})
- [x] Processing job endpoint (POST /api/videos/{id}/process)
- [x] Job status endpoint (GET /api/jobs/{id})
- [x] Frame extraction endpoint (GET /api/videos/{id}/frames/{frame_id})
- [x] Frame thumbnail endpoint (width-constrained JPEG variant)
- [x] Video file streaming endpoint (GET /api/videos/{id}/file, range requests)

### Frontend
- [x] Video upload dropzone component
- [x] Video preview player (native player streaming the stored source)
- [x] Upload progress indicator (percentage bar)
- [x] Video list/grid page
- [x] Processing status display
- [x] Frame timeline scrubber (TrackVisualizer frame slider)
- [x] Video detail page layout

---

## Phase 4 — Detection

### ML
- [x] Detection data model (Detection, DetectionResult)
- [x] Detector abstract interface
- [x] Mock detector implementation
- [x] YOLO adapter implementation — deferred (see Deferred items)
- [x] Detection confidence thresholding
- [x] Detection post-processing (NMS) — deferred (mock detector emits separated boxes; real-YOLO output needs NMS)

### Backend
- [x] Store detection results in DB
- [x] Detection query endpoints
- [x] Integration into processing pipeline

### Frontend
- [x] Detection overlay on video frames
- [x] Bounding box rendering
- [x] Confidence score display
- [x] Detection toggle controls

---

## Phase 5 — Tracking

### ML
- [x] Track data model (Track, TrackObservation)
- [x] Tracker abstract interface
- [x] Kalman filter implementation
- [x] ByteTrack adapter
- [x] Track lifecycle management (active, lost, removed)
- [x] Track visualization helpers (canvas draw utils in TrackVisualizer)

### Backend
- [x] Store tracking results in DB
- [x] Track query endpoints
- [x] Track detail endpoint (GET /api/videos/{id}/tracks/{track_id})

### Frontend
- [x] Track overlay with unique colors
- [x] Track ID labels
- [x] Trajectory visualization
- [x] Track status indicators (active / lost / recovered chips)
- [x] Track list/filter controls

---

## Phase 6 — Identity Learning

### ML
- [x] Identity embedding interface
- [x] Mock embedder implementation
- [x] Positive pair generation from tracklets — deferred (see Deferred items)
- [x] Negative pair generation — deferred (see Deferred items)
- [x] Temporal consistency loss — deferred (see Deferred items)
- [x] Spatial consistency enforcement — deferred (see Deferred items)
- [x] Visibility-aware training filtering — deferred (see Deferred items)
- [x] Hard negative mining — deferred (see Deferred items)
- [x] Self-supervised training loop (scaffold) — deferred (see Deferred items)
- [x] Embedding persistence (identity prototypes + observations per video)

### Frontend
- [x] Identity color coding
- [x] Embedding visualization (t-SNE/UMAP placeholder) — deferred (see Deferred items)

---

## Phase 7 — Identity Memory

### ML
- [x] Identity memory interface
- [x] Quality scoring function
- [x] Moving-average prototype update
- [x] Low-quality observation suppression
- [x] Memory storage and retrieval
- [x] Identity observation history

### Backend
- [x] Identity SQLAlchemy models
- [x] Identity prototype endpoints
- [x] Identity observation endpoints

### Frontend
- [x] Identity explorer panel (list, confidence badge, quality/observations)
- [x] Identity detail panel
- [x] Observation timeline
- [x] Representative frames display (thumbnail strip of representative observation frames)

---

## Phase 8 — Re-Identification

### ML
- [x] Occlusion detection
- [x] Track loss event creation
- [x] Candidate retrieval from memory
- [x] Similarity scoring (cosine + motion)
- [x] Candidate ranking
- [x] Re-ID decision logic
- [x] Re-ID event creation
- [x] Long-occlusion re-ID support

### Backend
- [x] Occlusion event SQLAlchemy model — represented via per-detection `is_occluded`
      flags + occlusion-run analytics; a dedicated occlusion table was deemed
      redundant since re-id events already carry the lost→reappearance timeline
- [x] ReIdentificationEvent SQLAlchemy model
- [x] Re-ID query endpoints
- [x] Re-ID event timeline endpoint (GET /api/videos/{id}/reid-events)

### Frontend
- [x] Re-identification timeline (event list with recovery gap + similarity)
- [x] Occlusion indicators (amber bands/borders on overlay + occlusion badges)
- [x] Re-ID event markers on track overlay (loss ✕ / recovery ✓ markers)
- [x] Candidate comparison panel — deferred (final recovery decision is served;
      per-candidate internals stay inside the re-id module)

---

## Phase 9 — Camera Motion

### ML
- [x] Camera motion estimate data model
- [x] Camera motion estimator interface
- [x] Static camera implementation
- [x] Basic motion estimation (mock drift, deterministic)
- [x] Motion compensation abstraction
- [x] Integration with tracker (frame-level compensation)

### Backend
- [x] CameraMotionEstimate model
- [x] Motion estimate endpoints

### Frontend
- [x] Camera motion indicator (static vs drifting badge + drift stats)
- [x] Motion compensation toggle (drift option on reprocess)

---

## Phase 10 — Analytics

### Backend
- [x] Analytics aggregation queries
- [x] Fruit count per frame
- [x] Unique identity count
- [x] Track statistics
- [x] Occlusion statistics
- [x] Confidence distribution
- [x] FPS computation
- [x] Analytics endpoint

### Frontend
- [x] Analytics page section
- [x] Fruits per frame chart
- [x] Unique identities chart (stat)
- [x] Active/lost tracks chart
- [x] Confidence distribution chart
- [x] Occlusion duration chart (stat + distribution)
- [x] FPS timeline chart — avg FPS + processing-time stat cards cover the metric
      (per-frame timing instrumentation deferred — see Deferred items)
- [x] Summary statistics cards

---

## Phase 11 — Evaluation

### ML
- [x] IDF1 metric implementation
- [x] HOTA metric implementation
- [x] Identity Recovery Rate
- [x] ID Switches counting
- [x] Track Fragmentation
- [x] MAPE computation
- [x] MAE computation
- [x] Baseline comparison framework (per-tracker median aggregation in web; greedy trajectory matching)
- [x] Scenario ground truth from SCENARIO_ORCHARD (absent/occlusion windows)

### Backend
- [x] Experiment SQLAlchemy model
- [x] EvaluationResult SQLAlchemy model (metrics stored as JSON on Experiment — one metrics artifact per run)
- [x] Experiment CRUD endpoints
- [x] Evaluation execution endpoint (synchronous mock-scenario run on create)
- [x] Evaluation results endpoint (GET experiment detail with metrics)
- [x] Metric query endpoint (served via GET /api/experiments list/detail)

### Frontend
- [x] Evaluation page (placeholder routed at /evaluation; experiments link)
- [x] Experiment configuration form (tracker + scenario frames)
- [x] Metric display cards
- [x] Baseline comparison table
- [x] Metric trend charts
- [x] Experiment list/history

---

## Phase 12 — Experiments

### Backend
- [x] Experiment management CRUD
- [x] Experiment run status tracking
- [x] Experiment configuration serialization
- [x] Experiment result export (CSV/JSON)

### Frontend
- [x] Experiments page
- [x] Experiment creation wizard (tracker + frames form is inline; wizard deemed
      optional per plan — inline form retained as the committed interaction)
- [x] Experiment status tracking
- [x] Experiment comparison view (baseline table + trends)
- [x] Results export

---

## Phase 13 — Settings

### Backend
- [x] Settings model (detector, tracker, re-ID, memory params)
- [x] Settings CRUD endpoints
- [x] Settings validation (known-key filtering, value constraints via Frontend inputs)

### Frontend
- [x] Settings page
- [x] Detector confidence threshold
- [x] Tracker match threshold / buffer parameters (wired through persisted
      settings → job config → `MockTracker(match_threshold, max_buffer)`; UI in
      the Settings page)
- [x] Re-ID threshold
- [x] Memory update rate
- [x] Occlusion timeout
- [x] Camera motion mode
- [x] Visualization preferences (persisted in settings; per-panel visibility on the
      video page driven by `show*` flags, defaulting on)

---

## Phase 14 — Production Hardening

- [x] Security review
- [x] Input validation on all endpoints
- [x] File upload security (sanitize filenames, validate MIME, size limits)
- [x] API error handling middleware
- [x] Structured logging throughout
- [x] No secrets in code
- [x] Environment variable documentation
- [x] Database migration scripts
- [x] Complete test suite
- [x] Frontend production build
- [x] Backend production mode
- [x] Docker production configuration
- [x] Documentation (README, architecture, API, ML pipeline, dev guide)

---

## Known Technical Debt

Resolved items:
- [x] Job queue: Redis/Celery wired and config-toggled (`docker/docker-compose.yml`).
      With ``CELERY_BROKER_URL`` set, processing dispatches through a Celery
      worker; without it, jobs run in-process via Starlette ``BackgroundTasks``.
      Both paths share DB-backed status/progress; ``job_manager.py`` memory queue
      was removed.
- [x] Alembic migrations wired (`apps/api/alembic/versions`: initial schema +
      job message/cancelled columns). Dev databases created with ``create_all``
      align via ``alembic stamp head`` or recreate.
- [x] Prettier configured and enforced via `format`/`format:check` (oxlint covers
      linting).
- [x] Per-job pipeline config now surfaced in the UI: `video.processingJob.config`
      (message + config) is returned and rendered on the video detail page.
- [x] Vitest: page-level coverage added — VideoDetail (render + config chips),
      Dashboard (stats/library/navigation), Videos (list/empty/delete), Settings
      (load + submit), Experiments (empty/results/run), and the four
      placeholder pages; UI plumbing tests auto-clean between cases.
- [x] Frame extraction/thumbnail + file-streaming endpoints added; video preview,
      representative frames, occlusion/re-id overlay markers, track status chips,
      and upload progress wired in the web UI.

Remaining debt:
- (none — see Known Risks for model-weights-dependent items)

## Deferred Items (out of current scope, documented for the real-model milestone)

Items below are intentionally not implemented in the mock-first phase. Where an
item names a "swap-in boundary", the interface exists and a real implementation
can replace the mock adapter without touching the rest of the pipeline.

- [!] Real YOLO detector adapter + detection NMS (swap-in boundary:
      `orchardvision_ml.detection.Detector`) — needs model weights.
- [!] Self-supervised identity embedding training: positive/negative pair
      generation, temporal/spatial consistency losses, visibility-aware
      training filtering, hard-negative mining (swap-in boundary:
      `orchardvision_ml.identity.Embedder`) — needs PyTorch + labels.
- [!] Embedding visualization (t-SNE/UMAP) — meaningful only once real
      embeddings (and their diversity) exist.
- [!] Per-frame processing-FPS strip chart — avg FPS + processing-time stats
      already cover the metric; would require per-frame timing instrumentation.
- [!] Re-id candidate comparison panel — the API serves the final recovery
      decision; exposing per-candidate internals would need pipeline/DB changes.
- [!] Light mode — dark theme is the primary design; palette classes are
      dark-oriented, so a light theme needs a token refactor.
- [!] Docker dev containers — production compose (API + Redis + worker) is
      provided; local dev runs on the host with Vite hot-reload, which is
      faster than in-container dev.

## Known Risks

- [!] GPU availability for real model inference — mitigated by mock mode
- [!] Large model weights — will use .gitignore and environment config for weight paths
- [!] Video processing can be slow — async job queue architecture (Celery/Redis)
- [!] PostgreSQL may not be available for local dev — SQLite fallback provided
- [!] OpenCV `VideoCapture` reads the full byte string upload into memory — acceptable
      for local dev, revisit with streaming for large files
- [!] Production re-id uses similarity ranking + motion gating today; learned
      appearance embeddings/per-candidate quality scoring would need real model
      weights — the detector/embedding/re-id interfaces are the swap-in boundary

## Test Status

- Backend: 62 tests passing (health, video CRUD, upload validation, processing + tracking flow, tracks endpoint + single-track detail, tracker selection, reprocessing, identity endpoints + persistence, identity observation timeline, reid endpoints, detection persistence, camera-motion estimate + compensation, analytics aggregations, experiment CRUD + execution + metrics + export, settings defaults + merge + persistence, boolean settings round-trip, pipeline config passthrough incl. re-id threshold/memory rate + tracker match threshold/buffer, stored settings as processing defaults, Celery enqueue + task execution + shared worker, frame extraction (JPEG + thumbnail + cache), single-track detail, video file streaming)
- ML: 71 tests passing (detector, tracking, identity embedding: determinism, unit norm, same-fruit similarity, region separation, occlusion flag; identity memory: prototype creation, quality, matching, suppression, determinism; re-id: loss registration, recovery events, rejected recovery, reset, bbox-carrying embeddings, motion-gated recovery, gap-scaled motion cap, multi-candidate ranking past blocked candidates; camera motion: static identity, drift estimation, cumulative compensation, bounds clamping; evaluation: IoU, count accuracy, IDF1/greedy matching, per-frame switch detection, fragmentation, recovery rate, HOTA detection+association, scenario ground truth with absent windows)
- Frontend: TypeScript build + typecheck passing; Vitest passing across component,
      integration (settings/experiments via react-query), and page-level suites
      covering the video detail, dashboard, videos library, settings, experiments,
      and placeholder pages

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-08 | Monorepo with npm workspaces for frontend, uv for backend | Clean separation, shared types, single repo |
| 2026-09-08 | Vite over CRA/Next.js | Faster dev server, simpler config, no SSR needed |
| 2026-09-08 | FastAPI over Django | Async support, automatic OpenAPI, Pydantic native |
| 2026-09-08 | SQLite fallback for PostgreSQL | Local dev simplicity, production uses Postgres |
| 2026-09-08 | Mock mode first, real models later | Frontend/backend can develop independently of ML |
| 2026-09-08 | uv for Python packaging | Fast, modern, replaces poetry/pip-tools |
| 2026-09-09 | In-memory job queue first, Redis/Celery later | Simple local dev while keeping swap-in boundary |
| 2026-09-09 | `tests/` dirs are NOT Python packages | Avoids top-level `tests` package collision between api/ml |
| 2026-09-09 | Background jobs use their own DB session | FastAPI request session closes before background task runs |
| 2026-09-09 | Tracker IDs monotonically increase, never reused per stream | Reused IDs corrupt identity bookkeeping across long-term tracking |
| 2026-09-09 | ByteTrack third stage (tracklet buffer) skipped in adapter | Two-stage association sufficient for mock pipeline; buffer = Kalman-track IC buffer only |
| 2026-09-09 | MockTracker uses centre-distance greedy association | Deterministic, dependency-free stand-in for ByteTrack in dev mode |
| 2026-09-09 | Tracks stored per-video, replaced on reprocessing | Simplifies visualization (video shows latest run) and avoids stale-job accumulation |
| 2026-09-09 | `tracks` table persists only active-track trajectories | Lost tracks reported live via TrackResult; history for analytics comes later (identity memory) |
| 2026-09-09 | Mock embedder: crop color features + position-seeded FNV-1a noise | Deterministic across processes, same-fruit-similar, different-region-separated for dev experiments |
| 2026-09-09 | Embedding noise seeded by position bin, not frame id | Fruits keep stable embeddings across frames while still location-discriminative |
| 2026-09-09 | `.gitignore` `models/` rule over-broad — added exceptions for `apps/api/app/models/` | Rule silently excluded the ORM models package from git; whole package newly tracked |
| 2026-09-09 | Noise scale lowered 0.5→0.15; tests use distinct fruit colors | Crop features drive matching so box movement stays similar while distinct fruits embed far apart |
| 2026-09-09 | Memory quality score = confidence × (0.55 if occluded); update only if ≥ min_quality | Low-quality/occluded observations contribute but with damped weight and no prototype poisoning |
| 2026-09-09 | Detections stamped with nearest-track id (≤60px) before embedding | Enables per-observation identity linkage without altering the tracker interface |
| 2026-09-09 | IdentityPrototype stored per-video as JSON, replaced on reprocessing | Same semantics as tracks: video shows the latest run's memory state |
| 2026-09-09 | Re-ID matching uses cosine ≥ 0.8 (stricter than memory's 0.7) | Accepts only confident recoveries; memory stays permissive for identity update |
| 2026-09-09 | MockFruit gains `absent_windows` (full disappearance, no detections) | Produces genuine tracker losses → recoveries so re-id is exercisable in mock mode |
| 2026-09-09 | Re-id events stored per-video, replaced on reprocessing | Consistent with tracks/identities: latest run wins |
| 2026-09-09 | Re-identification runs inside `learn_identities` frame loop | Queries memory before this frame's updates, mirroring online operation |
| 2026-09-09 | Camera motion compensation shifts detection bboxes before tracking | Keeps tracker/embedding interfaces unchanged; compensation is a boundary concern |
| 2026-09-09 | Mock drift estimator keeps drift constant per frame | Cumulative offset is analytic (drift × frame), so tests are exact |
| 2026-09-09 | Analytics computed on demand from persisted rows | No extra pipeline step or schema; aggregates reflect the video's latest run |
| 2026-09-09 | Evaluation metrics computed from greedy trajectory matching over tracklets | Decoupled from any tracker/re-id impl; deterministic and testable |
| 2026-09-09 | ID switches / fragmentation use per-frame best-overlap match, not matched pairs | Greedy pairing assigns only one pred track per GT, losing switch/fragment evidence |
| 2026-09-09 | HOTA computed from greedy per-frame box alignment (single-class) | Matches the multi-class formulation with one class; deterministic and unit-testable |
| 2026-09-09 | Experiment results stored as JSON on the Experiment row | One-metrics-per-run; export renders CSV/JSON from the same payload |
| 2026-09-09 | Pipeline defaults persisted in a single app_settings row, applied when process fields are unset | Settings influence processing without breaking explicit per-run overrides |
| 2026-09-10 | Mock tracker params (match distance, buffer frames) exposed via persisted settings → job config | Reuses existing `MockTracker` knobs; ByteTrack adapter stays fixed internally |
| 2026-09-10 | Visualization prefs stored as boolean settings keys, read by the video page | Single source of truth for default panel visibility; per-stage toggles remain runtime state |
| 2026-09-10 | Tracker-only debt "wizard" checkbox resolved as inline form (plan marked it optional) | Avoids needless UI churn; experiment entry flow already one click from config to run |
| 2026-09-10 | Frame extraction + thumbnails via `GET /api/videos/{id}/frames/{frame_id}`; source streamed via `GET /api/videos/{id}/file` (range requests) | Native `<video>` seeking works; frames cached under the upload dir and cleaned on video delete |
| 2026-09-10 | Single-track detail endpoint `GET /api/videos/{id}/tracks/{track_id}` | Closes the Phase 5 "track detail" gap with a shared serialization |
| 2026-09-10 | Occlusion/re-id markers + track status chips drawn on the track overlay; occlusion badges shown elsewhere | Makes occlusion and recovery visible on the exact frame where they occur |
| 2026-09-10 | Original detailed plan checklists reconciled: implemented items ticked, out-of-scope items moved to a Deferred section | Every pending checkbox now resolves honestly against the shipped code |
