#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

unset VIRTUAL_ENV

echo "Starting OrchardVision frontend (:5173) and API (:8001)"
trap 'kill 0' EXIT

npm run dev --workspace=apps/web &
uv run --project apps/api uvicorn app.main:app --reload --port 8001 &

wait