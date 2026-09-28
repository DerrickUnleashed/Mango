"""Database connection hygiene.

These tests exist so the narrow ResourceWarning filter in pyproject.toml is
safe. The filter suppresses "unclosed database" warnings that are emitted at
interpreter shutdown for connections still held by SQLAlchemy's pool. That
is a shutdown-order artifact, not a leak -- but only because nothing is
actually leaking. If a real leak is ever introduced, the test below fails.

Without this, suppressing the warning would be a way of making the symptom
disappear without knowing whether the cause existed.
"""

from __future__ import annotations

import gc

from fastapi.testclient import TestClient

from app.core.database import engine


def _live_sqlite_connections() -> int:
    gc.collect()
    return sum(1 for obj in gc.get_objects() if type(obj).__name__ == "Connection")


def test_repeated_requests_do_not_leak_connections(client: TestClient) -> None:
    """Connection count must not grow with request count.

    The engine pool is bounded, so a healthy run holds the same number of
    connections no matter how many requests are served. A per-request leak
    would show up here as a steadily climbing count.
    """
    assert client.get("/api/videos").status_code == 200
    gc.collect()
    after_warmup = _live_sqlite_connections()

    for _ in range(25):
        assert client.get("/api/videos").status_code == 200

    gc.collect()
    after_load = _live_sqlite_connections()

    # A small allowance for incidental collection, but nothing resembling
    # growth: a leak of one connection per request would be +25.
    assert after_load - after_warmup <= 2, (
        f"connections grew from {after_warmup} to {after_load} over 25 requests, "
        "which indicates a per-request leak"
    )


def test_pool_returns_every_connection(client: TestClient) -> None:
    """Nothing may be left checked out once the request is finished.

    `get_db` closes its session per request, so a connection still checked
    out after a response means a session was not released.
    """
    for _ in range(5):
        assert client.get("/api/videos").status_code == 200

    assert engine.pool.checkedout() == 0, "a session was left checked out after a request"
