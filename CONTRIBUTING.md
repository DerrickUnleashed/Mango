# Contributing to OrchardVision

Thank you for contributing! This guide covers how to set up the project and
land changes cleanly.

## Repository structure

OrchardVision is a multi-package monorepo:

- `apps/api` — FastAPI backend (`orchardvision-api`, uv-managed)
- `apps/web` — React + Vite frontend (npm workspace)
- `ml` — Python ML package (`orchardvision-ml`, uv-managed)
- `packages/*` — shared TypeScript contracts
- `docker/` — development and deployment containers

## Environment setup

### Prerequisites

- Node.js >= 22
- Python >= 3.12
- uv >= 0.5
- Docker (optional, for running the full dev stack)

### Install dependencies

```bash
# Python: API + ML workspace
uv sync --project apps/api --group dev
uv sync --project ml

# TypeScript: all npm workspaces
npm install
```

### Environment variables

Copy the API environment file and adjust values as needed:

```bash
cp apps/api/.env.example apps/api/.env
```

Never commit `.env` or any real secret.

## Daily development workflow

### Python (API + ML)

```bash
# Run the API tests
uv run --project apps/api pytest apps/api/tests -q
uv run --project ml pytest ml/tests -q

# Lint and format
uv run --project apps/api ruff check apps/api/app apps/api/tests
uv run --project apps/api ruff format --check apps/api/app apps/api/tests
```

Ruff is configured in `apps/api/pyproject.toml` (line length 100, target
`py312`, `E/F/W/I/B/UP/S` rule set). Keep `ruff check` and
`ruff format --check` clean before pushing.

### TypeScript (web + packages)

```bash
# Typecheck
npm run typecheck --workspace=apps/web

# Lint, format, tests
npx --yes oxlint@1.82.0      # from apps/web
npm run format:check --workspace=apps/web
npm run test --workspace=apps/web
```

### Running the dev stack

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

The API is served on `localhost:8001`; the Vite dev server proxies `/api`
requests to it. Watch the logs for the worker to confirm processing jobs run.

## Branching and commit conventions

- Cut feature and fix branches from `main` (never from long-lived feature
  branches).
- Use one branch per concern; keep branches small and focused.
- Commits use [conventional commits](https://www.conventionalcommits.org) —
  e.g. `feat(web): ...`, `fix(api): ...`, `docs: ...`, `chore: ...`.
- Write a subject line of a few words; the message describes what and why.

## Pull requests

- Open a PR when the branch is ready for review; reference the issue.
- Keep the diff focused. Reviewers expect checks (backend and frontend CI) to
  pass before merging.
- Do not merge changes that regress `ruff check`, typecheck, or the test
  suites.