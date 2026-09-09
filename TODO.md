# OrchardVision — Implementation TODO

## Current Status

**Phase:** 5 — Tracking (pipeline integration + persistence)
**Milestone:** Tracking stage wired into processing pipeline; tracks persisted and queryable via API
**Overall Progress:** 25%
**Last Updated:** 2026-09-09

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
- [ ] Responsive layout
- [ ] Desktop support
- [ ] Mobile-friendly behavior
- [ ] Keyboard navigation
- [ ] Accessible buttons/forms
- [ ] Loading states
- [ ] Empty states
- [ ] Error states
- [ ] Toast/notification system
- [ ] No dead navigation links

### QG 3 — Video Pipeline
- [ ] Video upload
- [ ] Upload validation (type, size)
- [ ] Video metadata extraction
- [ ] Video preview
- [ ] Processing state
- [ ] Job status
- [ ] Processing errors
- [ ] Result retrieval
- [ ] Frame navigation

### QG 4 — Detection
- [ ] Detector interface implemented
- [ ] Mock detector works
- [ ] Real YOLO adapter implemented
- [ ] Bounding boxes returned
- [ ] Confidence scores returned
- [ ] Detection visualization works
- [ ] Confidence threshold configurable
- [ ] Inference errors handled
- [ ] Detector unit tests pass

### QG 5 — Tracking
- [x] Tracker interface implemented
- [x] ByteTrack integration works
- [x] Track IDs persist across frames
- [x] Track lifecycle works
- [x] Lost tracks represented
- [ ] Track visualization works
- [x] Kalman/motion state represented
- [x] Tracker tests pass

### QG 6 — Identity Learning
- [ ] Embedding interface implemented
- [ ] Mock embedding model available
- [ ] Positive pair generation
- [ ] Negative pair generation
- [ ] Temporal consistency representation
- [ ] Spatial consistency representation
- [ ] Visibility filtering
- [ ] Hard-negative mechanism
- [ ] Identity embeddings persisted
- [ ] Embedding tests pass

### QG 7 — Identity Memory
- [ ] Identity prototype creation
- [ ] Quality score
- [ ] Confidence-aware update
- [ ] Moving-average update
- [ ] Low-quality observation suppression
- [ ] Memory persistence
- [ ] Memory retrieval
- [ ] Memory tests pass

### QG 8 — Re-Identification
- [ ] Track-loss detection
- [ ] Occlusion state
- [ ] Historical prototype search
- [ ] Similarity scoring
- [ ] Candidate ranking
- [ ] Re-ID threshold
- [ ] Successful re-identification
- [ ] Rejected re-identification
- [ ] Identity recovery visualization
- [ ] Re-ID tests

### QG 9 — Camera Motion
- [ ] Camera motion interface
- [ ] Static-camera mode
- [ ] Motion-compensation abstraction
- [ ] Camera motion metadata
- [ ] Tracker integration
- [ ] Tests for motion scenarios

### QG 10 — Analytics
- [ ] Fruit count
- [ ] Unique fruit count
- [ ] Active tracks
- [ ] Lost tracks
- [ ] Recovered identities
- [ ] ID switches
- [ ] Fragmentation
- [ ] Occlusion statistics
- [ ] Processing FPS
- [ ] Detection statistics

### QG 11 — Evaluation
- [ ] IDF1
- [ ] HOTA
- [ ] Identity Recovery Rate
- [ ] ID Switches
- [ ] Track Fragmentation
- [ ] MAPE
- [ ] MAE
- [ ] Baseline comparison
- [ ] Experiment configuration
- [ ] Exportable results

### QG 12 — Production Readiness
- [ ] Security review
- [ ] Input validation
- [ ] File validation
- [ ] API error handling
- [ ] Logging
- [ ] No secrets committed
- [ ] Environment configuration
- [ ] Database migrations
- [ ] Test suite complete
- [ ] Build succeeds
- [ ] Documentation complete

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
- [ ] Configure Docker (dev containers for frontend, backend, db)
- [x] Configure linting (ESLint/oxlint + Ruff)
- [x] Configure formatting (Prettier + Ruff format)
- [x] Configure testing (Vitest + pytest)
- [x] Create .env.example
- [ ] Create base Dockerfiles
- [x] Verify frontend↔backend communication (health + videos endpoints)
- [x] Verified end-to-end mock pipeline (upload → process → job status → complete)

---

## Phase 2 — UI Foundation

- [ ] Application shell (layout, sidebar, header)
- [ ] Navigation component with routes
- [ ] Dark theme (primary) + light mode
- [ ] Dashboard page (overview cards, placeholder charts)
- [ ] React Router configuration
- [ ] TanStack Query provider
- [ ] Global error boundary
- [ ] Toast/notification system
- [ ] Responsive layout foundation
- [ ] Loading spinner / skeleton components

---

## Phase 3 — Video Infrastructure

### Backend
- [ ] Video SQLAlchemy model
- [ ] ProcessingJob SQLAlchemy model
- [ ] Video upload endpoint (POST /api/videos)
- [ ] Video upload validation (MIME, size, format)
- [ ] Video metadata extraction (OpenCV)
- [ ] Video list endpoint (GET /api/videos)
- [ ] Video detail endpoint (GET /api/videos/{id})
- [ ] Video delete endpoint (DELETE /api/videos/{id})
- [ ] Processing job endpoint (POST /api/videos/{id}/process)
- [ ] Job status endpoint (GET /api/jobs/{id})
- [ ] Frame extraction endpoint (GET /api/videos/{id}/frames)
- [ ] Frame thumbnail endpoint (GET /api/videos/{id}/frames/{frame_id})

### Frontend
- [ ] Video upload dropzone component
- [ ] Video preview player
- [ ] Upload progress indicator
- [ ] Video list/grid page
- [ ] Processing status display
- [ ] Frame timeline scrubber
- [ ] Video detail page layout

---

## Phase 4 — Detection

### ML
- [x] Detection data model (Detection, DetectionResult)
- [x] Detector abstract interface
- [x] Mock detector implementation
- [ ] YOLO adapter implementation
- [ ] Detection confidence thresholding
- [ ] Detection post-processing (NMS)

### Backend
- [ ] Store detection results in DB
- [ ] Detection query endpoints
- [x] Integration into processing pipeline

### Frontend
- [ ] Detection overlay on video frames
- [ ] Bounding box rendering
- [ ] Confidence score display
- [ ] Detection toggle controls

---

## Phase 5 — Tracking

### ML
- [x] Track data model (Track, TrackObservation)
- [x] Tracker abstract interface
- [x] Kalman filter implementation
- [x] ByteTrack adapter
- [x] Track lifecycle management (active, lost, removed)
- [ ] Track visualization helpers

### Backend
- [x] Store tracking results in DB
- [x] Track query endpoints
- [ ] Track detail endpoint

### Frontend
- [ ] Track overlay with unique colors
- [ ] Track ID labels
- [ ] Trajectory visualization
- [ ] Track status indicators
- [ ] Track list/filter controls

---

## Phase 6 — Identity Learning

### ML
- [ ] Identity embedding interface
- [ ] Mock embedder implementation
- [ ] Positive pair generation from tracklets
- [ ] Negative pair generation
- [ ] Temporal consistency loss
- [ ] Spatial consistency enforcement
- [ ] Visibility-aware training filtering
- [ ] Hard negative mining
- [ ] Self-supervised training loop (scaffold)
- [ ] Embedding persistence

### Frontend
- [ ] Identity color coding
- [ ] Embedding visualization (t-SNE/UMAP placeholder)

---

## Phase 7 — Identity Memory

### ML
- [ ] Identity memory interface
- [ ] Quality scoring function
- [ ] Moving-average prototype update
- [ ] Low-quality observation suppression
- [ ] Memory storage and retrieval
- [ ] Identity observation history

### Backend
- [ ] Identity SQLAlchemy models
- [ ] Identity prototype endpoints
- [ ] Identity observation endpoints

### Frontend
- [ ] Identity explorer page
- [ ] Identity detail panel
- [ ] Observation timeline
- [ ] Representative frames display

---

## Phase 8 — Re-Identification

### ML
- [ ] Occlusion detection
- [ ] Track loss event creation
- [ ] Candidate retrieval from memory
- [ ] Similarity scoring (cosine + motion)
- [ ] Candidate ranking
- [ ] Re-ID decision logic
- [ ] Re-ID event creation
- [ ] Long-occlusion re-ID support

### Backend
- [ ] Occlusion event SQLAlchemy model
- [ ] ReIdentificationEvent SQLAlchemy model
- [ ] Re-ID query endpoints
- [ ] Re-ID event timeline endpoint

### Frontend
- [ ] Re-identification timeline
- [ ] Occlusion indicators
- [ ] Re-ID event markers
- [ ] Identity recovery visualization
- [ ] Candidate comparison panel

---

## Phase 9 — Camera Motion

### ML
- [ ] Camera motion estimate data model
- [ ] Camera motion estimator interface
- [ ] Static camera implementation
- [ ] Basic motion estimation (frame differencing)
- [ ] Motion compensation abstraction
- [ ] Integration with tracker

### Backend
- [ ] CameraMotionEstimate model
- [ ] Motion estimate endpoints

### Frontend
- [ ] Camera motion indicator
- [ ] Motion compensation toggle

---

## Phase 10 — Analytics

### Backend
- [ ] Analytics aggregation queries
- [ ] Fruit count per frame
- [ ] Unique identity count
- [ ] Track statistics
- [ ] Occlusion statistics
- [ ] Confidence distribution
- [ ] FPS computation
- [ ] Analytics endpoint

### Frontend
- [ ] Analytics page
- [ ] Fruits per frame chart
- [ ] Unique identities chart
- [ ] Active/lost tracks chart
- [ ] Confidence distribution chart
- [ ] Occlusion duration chart
- [ ] FPS timeline chart
- [ ] Summary statistics cards

---

## Phase 11 — Evaluation

### ML
- [ ] IDF1 metric implementation
- [ ] HOTA metric implementation
- [ ] Identity Recovery Rate
- [ ] ID Switches counting
- [ ] Track Fragmentation
- [ ] MAPE computation
- [ ] MAE computation
- [ ] Baseline comparison framework

### Backend
- [ ] Experiment SQLAlchemy model
- [ ] EvaluationResult SQLAlchemy model
- [ ] Experiment CRUD endpoints
- [ ] Evaluation execution endpoint
- [ ] Evaluation results endpoint
- [ ] Metric query endpoint

### Frontend
- [ ] Evaluation page
- [ ] Experiment configuration form
- [ ] Metric display cards
- [ ] Baseline comparison table
- [ ] Metric trend charts
- [ ] Experiment list/history

---

## Phase 12 — Experiments

### Backend
- [ ] Experiment management CRUD
- [ ] Experiment run status tracking
- [ ] Experiment configuration serialization
- [ ] Experiment result export (CSV/JSON)

### Frontend
- [ ] Experiments page
- [ ] Experiment creation wizard
- [ ] Experiment status tracking
- [ ] Experiment comparison view
- [ ] Results export

---

## Phase 13 — Settings

### Backend
- [ ] Settings model (detector, tracker, re-ID, memory params)
- [ ] Settings CRUD endpoints
- [ ] Settings validation

### Frontend
- [ ] Settings page
- [ ] Detector confidence threshold
- [ ] Tracker parameters
- [ ] Re-ID threshold
- [ ] Memory update rate
- [ ] Occlusion timeout
- [ ] Camera motion mode
- [ ] Visualization preferences

---

## Phase 14 — Production Hardening

- [ ] Security review
- [ ] Input validation on all endpoints
- [ ] File upload security (sanitize filenames, validate MIME, size limits)
- [ ] API error handling middleware
- [ ] Structured logging throughout
- [ ] No secrets in code
- [ ] Environment variable documentation
- [ ] Database migration scripts
- [ ] Complete test suite
- [ ] Frontend production build
- [ ] Backend production mode
- [ ] Docker production configuration
- [ ] Documentation (README, architecture, API, ML pipeline, dev guide)

---

## Known Technical Debt

- [!] In-memory job queue (job_manager) — must be replaced with Redis/Celery for
      production concurrency. Documented in `job_manager.py`.
- [!] Database tables created via `create_all` in dev; Alembic migrations not yet
      configured (config files present in `apps/api/alembic/` but unused).
- [!] Vitest not yet configured for frontend — component tests are pending.
- [!] Prettier not yet configured (oxlint covers frontend linting).

## Known Risks

- [!] GPU availability for real model inference — mitigated by mock mode
- [!] Large model weights — will use .gitignore and environment config for weight paths
- [!] Video processing can be slow — async job queue architecture
- [!] PostgreSQL may not be available for local dev — will provide SQLite fallback
- [!] OpenCV `VideoCapture` reads the full byte string upload into memory — acceptable
      for local dev, revisit with streaming for large files

## Test Status

- Backend: 14 tests passing (health, video CRUD, upload validation, processing + tracking flow, tracks endpoint, tracker selection, reprocessing)
- ML: 18 tests passing (detector interface, mock determinism, occlusion windows, tracker interface, mock tracker lifecycle, ByteTrack two-stage association, Kalman)
- Frontend: TypeScript build + typecheck passing; component tests pending (Vitest)

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
