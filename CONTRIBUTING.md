# Contributing to OrchardVision

Thank you for contributing! This guide covers how to set up the project and
land changes cleanly.

Participation in this project is governed by
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

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
cp .env.example .env
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
uv run --project ml ruff check ml/orchardvision_ml ml/tests
uv run --project ml ruff format --check ml/orchardvision_ml ml/tests
```

Ruff is configured identically in `apps/api/pyproject.toml` and
`ml/pyproject.toml` (line length 100, target `py312`, `E/F/W/I/B/UP/S` rule
set). Both packages are linted in CI, so keep `ruff check` and
`ruff format --check` clean for `ml/` as well as the API.

### TypeScript (web + packages)

```bash
# Typecheck (runs every workspace)
npm run typecheck

# Lint, format, tests
npm run lint --workspace=apps/web
npm run format:check
npm test
```

`npm run typecheck`, `npm run format:check`, and `npm test` each fan out across
all workspaces (`--workspaces --if-present`), so they cover both `apps/web` and
`packages/types` without naming a workspace. Linting is the one exception:
`npm run lint --workspace=apps/web` is named explicitly because oxlint is
configured per app via `apps/web/.oxlintrc.json` and runs from the lockfile
rather than a hardcoded `npx` version. Prettier config is shared from the
repo-root `.prettierrc.json`; add new packages inside that tree rather than
introducing a second config.

### Running the dev stack

```bash
docker compose -f docker/docker-compose.yml up --build
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
