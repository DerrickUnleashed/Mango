# OrchardVision Documentation

## Overview

OrchardVision is a computer vision system for long-term fruit tracking and counting in mango orchards. It implements identity learning, tracking pipelines, and a full-stack web interface for experiment management and video processing.

## Architecture

### Backend (FastAPI)

- **Framework**: FastAPI with SQLAlchemy 2.0 ORM
- **Database**: SQLite (dev), PostgreSQL (production via `DATABASE_URL`)
- **API**: REST under `/api/v1/` with router prefixes:
  - `GET /health` - service status
  - `POST/GET/DELETE /videos` - video upload/listing/management
  - `GET /videos/{id}/tracks` - track trajectories
  - `GET /videos/{id}/identities` - identity prototypes
  - `POST /videos/{id}/process` - start processing job
  - `GET /jobs/{id}` - job status
  - `GET/POST/DELETE /experiments` - evaluation harness
  - `GET/PUT /settings` - pipeline defaults

### Frontend (React + TypeScript)

- Shared types from `packages/types/src/`
- Components in `apps/web/src/`
- API client calls to FastAPI backend

### Core Services

- **ProcessingPipeline**: Orchestrates frame extraction → detection → tracking → embedding → analytics
- **EmbeddingProjection**: t-SNE / PCA visualization of identity prototypes
- **AnalyticsEngine**: Computes IDF1, HOTA, ID switches metrics
- **StorageService**: MinIO/S3-backed file management for uploads and frames

### Configuration

- Loaded via `pydantic_settings` from `.env`
- Key settings: confidence threshold, ReID threshold, tracker type, camera motion mode, memory update rate, tracker match threshold, buffer frames
- Persisted in `AppSettings` table (single row, `GLOBAL_SETTINGS_ID`)

## Data Models

| Model | Key Fields |
|-------|-----------|
| `Video` | `id`, `filename`, `width`, `height`, `fps`, `frame_count`, `status` |
| `ProcessingJob` | `id`, `video_id`, `status`, `stage`, `progress`, `config` dict |
| `Experiment` | `id`, `name`, `tracker`, `scenario`, `num_frames`, `status`, `metrics` |
| `IdentityRecord` | `id`, `video_id`, `identity_id`, `prototype` (embedding vector), `quality`, `observation_count`, `is_confident` |
| `Track` | `id`, `video_id`, `track_id`, `frames`, `first_seen`, `last_seen` |
| `DetectionRecord` | `id`, `video_id`, `frame_id`, `bbox`, `confidence` |
| `FrameTimingRecord` | `id`, `video_id`, `frame_id`, `proc_ms` |
| `CameraMotionRecord` | `id`, `video_id`, `motion_type`, `compensation_applied` |
| `IdentityObservation` | `id`, `video_id`, `identity_id`, `track_id`, `frame_id` |
| `ReidEvent` | `id`, `video_id`, `lost_frame_id`, `reappearance_frame_id` |
| `AppSettings` | `id` (=`GLOBAL_SETTINGS_ID`), `values` dict |

## Pipeline Flow

1. **Upload**: User POSTs video → `storage_service.save_upload` → `extract_video_metadata` → `Video` row created, status=`uploaded`
2. **Process**: POST `/videos/{id}/process` → validates no active job → creates `ProcessingJob` status=`QUEUED` → enqueues (Celery) or runs sync → background task processes frames:
   - Frame extraction per `PipelineConfig`
   - Object detection (model specified by `model_path`)
   - Tracking (mock/bytetrack/tapnext)
   - Re-identification embeddings
   - Identity consolidation
   - Analytics computation (`compute_video_analytics`)
   - Updates `Video` status → `processed`, creates `IdentityRecord`s, `Track`s, `DetectionRecord`s, `FrameTimingRecord`s, `CameraMotionRecord`
3. **Retrieve**: GET endpoints return persisted tracks, identities, analytics, frame timings, motion estimates, ReID events, detections

## API Endpoints (Summary)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health |
| POST | `/videos` | Upload video |
| GET | `/videos` | List videos |
| GET | `/videos/{id}` | Video metadata |
| GET | `/videos/{id}/tracks` | Track trajectories |
| GET | `/videos/{id}/identities` | Identity prototypes |
| GET | `/videos/{id}/identities/projection` | 2D coordinates for visualization |
| GET | `/videos/{id}/identities/{identity_id}` | Specific identity |
| GET | `/videos/{id}/identities/{identity_id}/observations` | Per-frame observations |
| GET | `/videos/{id}/reid-events` | Re-identification events |
| GET | `/videos/{id}/detections` | Persisted detections |
| GET | `/videos/{id}/per-frame` | Per-frame timing telemetry |
| GET | `/videos/{id}/motion` | Camera motion estimate |
| GET | `/videos/{id}/analytics` | Aggregated analytics |
| DELETE | `/videos/{id}` | Delete video + all associated data |
| POST | `/videos/{id}/process` | Start processing job |
| GET | `/jobs/{id}` | Job status |
| GET | `/experiments` | List experiments |
| POST | `/experiments` | Create + run experiment |
| GET | `/experiments/{id}` | Experiment detail |
| GET | `/experiments/{id}/export` | Download results (JSON/CSV) |
| DELETE | `/experiments/{id}` | Delete experiment (cannot RUNNING) |
| GET | `/settings` | Pipeline defaults |
| PUT | `/settings` | Update pipeline defaults |

## TypeScript Types (shared)

Common interfaces in `packages/types/src/common.ts`:

- `BoundingBox` - `{ x: number, y: number, width: number, height: number }`
- `VisibilityState` - `'visible' \| 'occluded' \| 'lost'`
- `JobStatus` - `'uploaded' \| 'processing' \| 'processed' \| 'error'`
- `ProcessingStage` - `'frame_extraction'` → `'detection'` → `'tracking'` → `'reid'` → `'analytics'`
- `ProcessingStatus` - `'QUEUED'` → `'RUNNING'` → `'COMPLETED'` → `'FAILED'`
- `MultiVideoResponse`, `MultiTrackResponse`, `MultiIdentityResponse`, etc.

## Deployment

- **Development**: `uvicorn apps.api.app.main:app --reload` (SQLite at `./data/app.db`)
- **Production**: PostgreSQL via `DATABASE_URL`, gunicorn/uvicorn, behind reverse proxy
- **Frontend**: `npm run dev` (Vite) proxies `/api/` to backend
- **Upload limit**: 2GB max (configurable via `MAX_UPLOAD_BYTES` env var)
- **CORS**: localhost:5173 configured

## Error Handling

- All errors return `{"detail": "...", "code": "...", "status": ...}` format
- Custom exceptions: `ApiError` base, `NotFoundError`, `ConflictError`, `ValidationFailError`
- Global exception handler in `apps/api/app/main.py`

## Development

- Add new models/migrations via SQLAlchemy 2.0 model definitions
- Add new API routes in `apps/api/app/routers/`
- Add new schemas in `apps/api/app/schemas/`
- Add new services in `apps/api/app/services/`
- Run tests: `pytest` from repo root
- Type check: `pnpm exec tsc --noEmit` from `packages/types/`