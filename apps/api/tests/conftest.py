"""Pytest fixtures for API tests.

Important: the test database environment variable must be set *before* the app
modules are imported, because the engine is created at import time.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_tmpdir = tempfile.mkdtemp(prefix="orchardvision-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmpdir}/uploads"
os.environ["PROCESSED_DIR"] = f"{_tmpdir}/processed"
os.environ["AUTO_CREATE_TABLES"] = "true"


from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _dispose_engine() -> Iterator[None]:
    """Close the session's pooled connections when the run finishes.

    `app.core.database` creates its engine at import time and nothing
    disposes it, so the pooled SQLite connections are still open when the
    interpreter tears down. Best effort rather than a guarantee: disposing
    the engine does not close every pooled connection, which is why the
    narrow ResourceWarning filter in pyproject.toml exists alongside this.

    The absence of an actual leak is asserted by
    `test_database.py::test_repeated_requests_do_not_leak_connections`, so
    this fixture is hygiene, not the safety net.
    """
    yield
    from app.core.database import engine

    engine.dispose()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_video_bytes() -> bytes:
    """Return a small deterministic synthetic MP4 encoded with OpenCV."""
    import cv2
    import numpy as np

    handle, path = tempfile.mkstemp(suffix=".mp4")
    os.close(handle)
    try:
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 30, (640, 360))
        for _ in range(30):
            frame = np.full((360, 640, 3), 20, dtype=np.uint8)
            for f in range(4):
                x, y = 80 + f * 140, 100 + (f % 2) * 90
                cv2.circle(frame, (int(x), int(y)), 16, (0, 150, 210), -1)
            writer.write(frame)
        writer.release()
        data = Path(path).read_bytes()
    finally:
        Path(path).unlink(missing_ok=True)
    return data
