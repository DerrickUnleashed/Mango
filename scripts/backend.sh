#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

unset VIRTUAL_ENV

echo "Starting OrchardVision API on :8001"
uv run --project apps/api uvicorn app.main:app --reload --port 8001 "$@"