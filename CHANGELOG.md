# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.2.0] - 2026-10-17

TAPNext++ tracker release. Adds a point-enhanced fruit tracker to the
pipeline and closes out the evaluation and ground-truth tooling work.

### Added

- TAPNext++ point-enhanced fruit tracker (`#56`), selectable from the pipeline
  and reported alongside the existing trackers in the timing tables.
- TAPNext row in the tracker and timing comparison tables, generated from the
  downloaded checkpoint.
- `load_ground_truth()` reads Labelme-format annotations, so externally
  labelled videos can be evaluated without conversion.

### Fixed

- Docker runtime for the TAPNext++ finder.
- Docker and Vercel deploy configuration for the web workspace (`#70`).
- Docker actions bumped off the end-of-life Node 20 runtime.
- `source-map-js` bumped to 1.2.2 for GHSA-68fv-2mgg-jv7q.
- Ground-truth, evaluation, and plotting scripts updated for the TAPNext++
  results and rebuilt annotation sets.

## [0.1.0] - 2026-09-28

First tagged release. Covers the detection-to-evaluation pipeline, the web
client, and the repository infrastructure that grew alongside it.

### Added

- Six-stage processing pipeline: detection, camera-motion estimation,
  tracking, identity embedding, re-identification, and evaluation, with mock
  and real inference modes.
- FastAPI backend (`orchardvision-api`) with video upload, job queue, track
  and identity endpoints, and Celery worker support.
- ML package (`orchardvision-ml`) with mock and YOLO detectors, ByteTrack and
  Kalman trackers, visibility-aware identity learning, and re-identification.
- React 19 web client with track overlay, identity and re-identification
  panels, embedding map, motion panel, FPS strip, experiments, and settings.
- Docker image and Compose stack (API, worker, Redis) for local and deployed
  use.
- Alembic migrations, applied automatically at API startup.
- CI pipeline covering lint, typecheck, tests, and build for both stacks.
- Security scanning: gitleaks over full history, `pip-audit` on both Python
  trees, and `npm audit`, gated behind CI so they block a merge.
- Test coverage measurement and non-blocking ratchets for all three packages.
- Repository governance: `CODEOWNERS`, PR template, issue templates,
  Contributor Covenant, proprietary `LICENSE`, and Dependabot.

### Fixed

- Processing progress is now monotonic, so stages cannot rewind the reported
  percentage, and stage progress bands were retuned to a non-overlapping range.
- `frame_timings` had no migration; the chain now creates all 11 ORM tables.
- Deployments built from ORM metadata rather than migrations are stamped
  rather than upgraded, so an existing database is adopted instead of failing
  to boot.
- The API refuses to start in production with a placeholder `SECRET_KEY`.
- The Docker build context no longer ships `.git`, model weights, or local
  data — about 7.8 GB reduced to roughly 0.7 MB.
- New model weights are no longer committed; `.gitignore` covers `*.pt`.
- Track overlay strokes, dashes, and fonts scale with video resolution.
- `ml` no longer relies on `ultralytics` to pull in `torch`, which is now a
  declared optional extra.
- `packages/types` is covered by a format check, and a single shared Prettier
  config replaces the per-workspace drift.
- `ml` is linted in CI alongside the API, and oxlint runs from the lockfile
  rather than a hardcoded `npx` version.
- Two broken paths in `CONTRIBUTING.md` that failed on a clean clone.

[Unreleased]: https://github.com/DerrickUnleashed/Mango/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/DerrickUnleashed/Mango/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DerrickUnleashed/Mango/releases/tag/v0.1.0
