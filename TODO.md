# Project Tasks & Roadmap

## [ ] Verify + deploy: ship YOLO weights in image, fix WEIGHTS_DIR mismatch
- **Status:** Pending (paused — build aborted mid-flight, UNVERIFIED)
- **Created:** 2026-10-15 22:45
- **Category:** Fix

### Context / Goal
A real video upload on Render fails at detection:

```
FileNotFoundError: [Errno 2] No such file or directory:
  '/orchardvision/models/mango_yolov8n-4/weights/best.pt'
```

Upload and metadata extraction both succeed (`960x506 @ 29.97fps, 473 frames`
= `videos/test.mp4`). It dies in `_build_detector` -> `YoloDetector.__init__`.

Two independent causes, **both uncommitted and untested right now**:

1. The weight is tracked in git but excluded from the build context by
   `.dockerignore` (`models` and `*.pt`), and the Dockerfile never COPY'd it.
2. `docker/bootstrap_weights.py` writes to `WEIGHTS_DIR=/data/models`, but
   `processing.py:50` reads `settings.yolo_weights_path`, which defaults to
   `ROOT_DIR/models/...`. Even a successful download landed where nothing reads.
   Same bug for TAPNext via `settings.tapnext_checkpoint_path`.

### Action Items
- [ ] Finish the aborted build: `docker build -f docker/Dockerfile -t orchardvision-api:fix .`
- [ ] Assert the weight is actually in the image: `best.pt` present under `/orchardvision/models/`
- [ ] Load the model end-to-end inside the container, not just import it — that is what failed
- [ ] Confirm `settings.yolo_weights_path` and `settings.tapnext_checkpoint_path` now agree with `WEIGHTS_DIR`
- [ ] Re-run the failing job against production after deploy
- [ ] Commit only after the load is proven, not after the build goes green

### Technical Details / Notes
- Edits already made (uncommitted): `.dockerignore` re-includes
  `models/mango_yolov8n-4/weights/best.pt`; `Dockerfile` COPYs it to the exact
  default path; `WEIGHTS_DIR` default moved to `/orchardvision/models`.
- Docker cannot re-include a file under an excluded directory, so each level of
  `models/` must be re-opened in turn in `.dockerignore`.
- `best.pt` is 5.9M and already in git history — shipping it in the image beats
  fetching it at boot, and needs no credential or public URL.
- TAPNext++ is 2.4G and stays out of the context; bootstrap fetches it from
  public GCS. `/orchardvision` is an image layer on Render free, so a 2.4G
  re-download happens on every redeploy. Consider a Render disk at `/data`.

---

## [ ] Add DATABASE_URL — state is ephemeral SQLite
- **Status:** Blocked (needs Supabase DB password)
- **Created:** 2026-10-15 22:47
- **Category:** Fix

### Context / Goal
The service falls back to `sqlite:////data/orchardvision.db`. The Render free
plan has no persistent disk, so **uploaded videos and job state are lost on
every redeploy.** The uploaded `test.mp4` will vanish.

### Action Items
- [ ] User supplies password from Supabase -> Project Settings -> Database
- [ ] Set `DATABASE_URL` on the service (dashboard; do not paste the password into chat)
- [ ] Flip `AUTO_CREATE_TABLES` to `false` once Postgres is authoritative
- [ ] Verify the 3 alembic revisions (`5d307872fa5b`, `6e55088f8611`, `c7f1a4d9b2e3`) still match the applied schema

### Technical Details / Notes
- Connection string shape:
  `postgresql+psycopg://postgres.lfihhupxdbtcxituwhby:<pw>@aws-0-ap-south-1.pooler.supabase.com:6543/postgres`
- Supabase project `lfihhupxdbtcxituwhby`, ap-south-1, schema + RLS already applied to all 11 tables.
- `psycopg[binary]` already in `pyproject.toml`, so no new dependency.

---

## [ ] Ship TAPNext++ tracker weights
- **Status:** Pending (blocked on RAM/disk budget)
- **Created:** 2026-10-15 22:48
- **Category:** Feature

### Context / Goal
TAPNext++ is 2.4G. The public GCS object is confirmed live (`HTTP/2 200`), and
`bootstrap_weights.py` can fetch it on boot, but the free plan has ~512M RAM
and a small disk, so a 2.4G download on every cold start is likely unusable.

### Action Items
- [ ] Confirm which tracker the deployment actually needs (default may not be tapnext)
- [ ] Measure memory for a real detection pass, not just model load
- [ ] If too heavy: Render disk at `/data`, or drop to a non-tapnext tracker
- [ ] Enable `BOOTSTRAP_TAPNEXT=true` once the host can absorb it

### Technical Details / Notes
- URL: `https://storage.googleapis.com/dm-tapnet/tapnextpp/tapnextpp_ckpt.pt`
- Currently `BOOTSTRAP_TAPNEXT=false` and `DEFAULT_INFERENCE_MODE` handling is
  inconsistent — jobs still ran `real` despite the mock default; trace where the
  job's `inference_mode` is actually chosen.

---

## [ ] Ship trained identity embedder (44M)
- **Status:** Blocked (needs Supabase service_role key)
- **Created:** 2026-10-15 22:49
- **Category:** Feature

### Context / Goal
`models/identity/embedder.pt` (44M) is user-trained and not public. Real-mode
inference falls back to the torchvision backbone without it.

### Action Items
- [ ] User supplies Supabase `service_role` key (Storage API; the MCP has no storage tools)
- [ ] Upload `embedder.pt` and set `EMBEDDER_URL`
- [ ] Enable `BOOTSTRAP_EMBEDDER=true`
- [ ] Verify re-ID metrics match the local `identityRecoveryRate` 1.0 run

### Technical Details / Notes
- 44M + 5.9M fits well inside the 1GB free-tier Storage quota.
- TAPNext must NOT go in Storage — 2.4G exceeds free tier.

---

## [ ] Investigate ERR_BLOCKED_BY_CLIENT
- **Status:** Pending (low severity)
- **Created:** 2026-10-15 22:50
- **Category:** Fix

### Context / Goal
Browser console showed `net::ERR_BLOCKED_BY_CLIENT` on some requests to
`onrender.com`. That never reaches Render — it is an ad/uBlock extension
killing the request client-side.

### Action Items
- [ ] Reproduce with extensions disabled to confirm
- [ ] If reproducible, proxy `/api/*` through Vercel to Render (same-origin kills CORS *and* extension filtering)
- [ ] Weigh the extra hop + doubled cold start on the free tier

---

## [ ] Merge PR #70 and reconcile render.yaml
- **Status:** Pending
- **Created:** 2026-10-15 22:51
- **Category:** Documentation

### Action Items
- [ ] Merge PR #70 (`deploy/production` -> `main`) once the weight fix is verified
- [ ] `render.yaml` already carries the JSON-array `ALLOWED_ORIGINS` fix
- [ ] Update the misleading `Failed to load videos. Is the API running on port 8001?` hint in `DashboardPage.tsx:56` and `VideosPage.tsx:151` — the port is supplied by the host, never 8001 in prod
- [ ] Document the `VITE_API_URL` requirement, including that it must include the `/api` prefix

### Technical Notes
- Config traps found while deploying: list-typed settings must be JSON arrays,
  not comma-separated; `VITE_API_URL` must end in `/api`; managed hosts inject
  `$PORT` (Render used 10000).