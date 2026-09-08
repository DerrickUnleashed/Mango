#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Starting OrchardVision API on :8000"
uv run --project apps/api uvicorn app.main:app --reload --port 8000 "$@"