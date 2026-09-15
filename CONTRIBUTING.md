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