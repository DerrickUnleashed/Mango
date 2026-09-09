"""Production entrypoint for the OrchardVision API.

Usage:
    cd apps/api
    uv run python -m app

Reads ENVIRONMENT to pick worker count and log verbosity. Common production
variables: PORT, WEB_CONCURRENCY, ENVIRONMENT.
"""

from __future__ import annotations

import os

import uvicorn

from app.main import create_app


def _resolve_port() -> int:
    try:
        return int(os.environ.get("PORT", "8000"))
    except ValueError:
        return 8000


def _resolve_workers() -> int:
    environment = os.environ.get("ENVIRONMENT", "development").lower()
    if environment == "development":
        return 1
    try:
        return max(1, int(os.environ.get("WEB_CONCURRENCY", "2")))
    except ValueError:
        return 2


def main() -> None:
    environment = os.environ.get("ENVIRONMENT", "development").lower()
    workers = _resolve_workers()
    common = {
        "host": os.environ.get("HOST", "0.0.0.0"),  # noqa: S104  (server binding)
        "port": _resolve_port(),
        "log_level": "warning" if environment == "production" else "info",
    }
    if workers > 1:
        # uvicorn requires an import string (not an app instance) when forking workers.
        uvicorn.run("app.main:app", workers=workers, **common)
    else:
        uvicorn.run(create_app(), **common)


if __name__ == "__main__":
    main()
