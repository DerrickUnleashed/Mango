# OrchardVision

Visibility-aware, self-supervised identity learning for long-term fruit tracking
and counting in mango orchards.

Pan-tilt-zoom cameras make fruit appear, disappear, and re-appear as they sway
in the wind, occlude each other, and move across the view. OrchardVision learns
per-fruit identity descriptors from a detection stream and uses them to recover
identities after occlusion, so counts stay correct over long video runs.

## Repository layout

```
apps/api      FastAPI backend (uv workspace; package `app`)
apps/web      React + Vite + Tailwind frontend (npm workspace `web`)
packages/types Shared TypeScript contracts (npm workspace `types`)
ml            `orchardvision_ml` python package (uv workspace)
data          Local runtime data (uploads, processed, DB) — gitignored
docker        Container configuration
```

## Quickstart

### Backend

```bash
cp .env.example .env            # adjust as needed
uv run --project apps/api uvicorn app.main:app --port 8000 \
    --app-dir apps/api         # run from the repository root
```

- Interactive docs: `http://localhost:8000/api/docs`
- Health check: `http://localhost:8000/api/health`

### Frontend

```bash
cd apps/web
npm install
npm run dev                     # http://localhost:5173
```

### Tests & checks

```bash
uv run --project ml pytest ml/tests -q                 # ML suite
uv run --project apps/api pytest apps/api/tests -q     # API suite
uv run --project ml ruff check ml                      # ML lint
uv run --project apps/api ruff check apps/api          # API lint
cd apps/web && npm run typecheck && npm run lint && npm run build
```

## Architecture

Processing runs per video in a background thread:

1. **Detection** — mock detector emits fruit boxes per frame; real detectors plug
   in behind the same interface (`orchardvision_ml.detection`).
2. **Camera motion compensation** — estimates pan/tilt drift and shifts boxes
   before tracking (`static`/`drift`).
3. **Tracking** — mock identity-primitive tracker or a ByteTrack-style adapter
   (`orchardvision_ml.tracking`).
4. **Identity embedding + memory** — quality-aware prototypes per fruit with
   online prototype updates (`orchardvision_ml.identity.embedding`/`memory`).
5. **Re-identification** — after a track loss, queries identity memory to recover
   the same fruit (`orchardvision_ml.reid`).
6. **Evaluation harness** — scores trajectories against scenario ground truth:
   IDF1, HOTA, ID switches, fragmentation, count MAE/MAPE, identity recovery
   rate (`orchardvision_ml.evaluation`).

All per-video artifacts (tracks, identities, identity observations, re-id events,
per-frame detections, camera-motion estimate, analytics aggregates) are persisted
and re-computed on reprocessing; each pipeline level is mock-first so the whole
system runs without heavy model weights.

## API summary

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Service status |
| `POST /api/videos` | Upload video (MIME/extension/size validated) |
| `GET /api/videos` · `GET /api/videos/{id}` · `DELETE /api/videos/{id}` | Video CRUD |
| `POST /api/videos/{id}/process` | Start processing (mock/real, tracker, camera motion) |
| `GET /api/videos/{id}/tracks` | Track trajectories |
| `GET /api/videos/{id}/identities(/observations)` | Identity prototypes + observation history |
| `GET /api/videos/{id}/reid-events` | Re-identification events |
| `GET /api/videos/{id}/detections?frame_id=` | Per-frame persisted detections |
| `GET /api/videos/{id}/motion` · `GET /api/videos/{id}/analytics` | Motion estimate + aggregates |
| `GET/POST /api/experiments`, `GET/DELETE /api/experiments/{id}`, `GET /api/experiments/{id}/export` | Evaluation experiment runs (JSON/CSV export) |
| `GET/PUT /api/settings` | Persisted pipeline defaults |

Full schemas are in `apps/api/app/schemas/video.py`.

## Configuration

See `.env.example` for the authoritative list. Key variables:

- `DATABASE_URL` — default SQLite at `data/orchardvision.db`
- `UPLOAD_DIR`, `PROCESSED_DIR` — storage locations
- `MAX_UPLOAD_BYTES`, `ALLOWED_VIDEO_MIME_TYPES` — upload constraints
- `ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS` — CORS
- `AUTO_CREATE_TABLES` — dev-friendly `create_all`; set `false` and use `alembic up` for managed schemas, see below

## Database migrations

Alembic is wired (`apps/api/alembic`). Build the schema on a fresh database:

```bash
cd apps/api
alembic upgrade head
```

Existing dev databases created with `create_all` can be aligned with
`alembic stamp head` or recreated.

## Production notes

- Start the API with the production entrypoint, which reads
  `ENVIRONMENT`, `PORT`, `WEB_CONCURRENCY`, and `HOST`:

  ```bash
  ENVIRONMENT=production PORT=8000 WEB_CONCURRENCY=2 uv run --project apps/api python -m app
  ```

  or run `uvicorn app.main:app --workers N` directly. Place behind a reverse proxy
  (Caddy/nginx) for TLS.
- The in-memory job queue must be replaced with a distributed queue (Redis +
  Celery) for multi-worker deployments.
- Mock inference is the default; real models (YOLO, embedding net) swap in via
  the detection/embedding interfaces.

See `TODO.md` for the full phase map and known technical debt.