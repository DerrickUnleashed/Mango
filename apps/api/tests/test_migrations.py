"""Migration startup tests.

Covers the three database states `migrate.py` must handle at container
startup, most importantly the legacy one: a database built by
`init_models()` before migrations were wired up has tables but no alembic
history, and a naive `upgrade head` against it fails with
"table app_settings already exists" -- which would take down every existing
deployment on the image.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]


def _run_migrate(db_path: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}
    return subprocess.run(
        [sys.executable, "migrate.py"],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def _tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def _alembic_version(db_path: Path) -> str | None:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    return row[0] if row else None


def _expected_tables() -> set[str]:
    import app.models  # noqa: F401
    from app.core.database import Base

    return set(Base.metadata.tables)


def test_fresh_database_gets_full_chain(tmp_path: Path) -> None:
    db = tmp_path / "fresh.db"
    result = _run_migrate(db)

    assert result.returncode == 0, result.stderr
    assert "frame_timings" in _tables(db)
    assert _alembic_version(db) is not None


def test_migrated_schema_matches_orm(tmp_path: Path) -> None:
    """A migrated database must contain exactly the ORM's tables."""
    db = tmp_path / "match.db"
    assert _run_migrate(db).returncode == 0

    assert _tables(db) - {"alembic_version"} == _expected_tables()


def test_legacy_database_is_stamped_not_upgraded(tmp_path: Path) -> None:
    """A pre-migration database has tables but no alembic history.

    This is the deployment-break scenario: `upgrade head` raises
    "table app_settings already exists" against such a database.
    """
    db = tmp_path / "legacy.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}"}
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.core.database import init_models; init_models()",
        ],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "alembic_version" not in _tables(db), "fixture should be a pre-migration database"

    result = _run_migrate(db)

    assert result.returncode == 0, result.stderr
    assert "stamping" in result.stdout
    assert _alembic_version(db) is not None
    assert _tables(db) - {"alembic_version"} == _expected_tables()


def test_legacy_database_data_survives(tmp_path: Path) -> None:
    """Stamping must adopt the existing schema, not recreate it."""
    db = tmp_path / "data.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}"}
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.core.database import init_models, SessionLocal\n"
                "from app.models import Video\n"
                "init_models()\n"
                "s = SessionLocal()\n"
                "s.add(Video(id='v1', original_name='keep.mp4', filename='keep.mp4',"
                " mime_type='video/mp4', size_bytes=1, status='uploaded'))\n"
                "s.commit()\n"
            ),
        ],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert _run_migrate(db).returncode == 0

    with sqlite3.connect(db) as conn:
        names = [row[0] for row in conn.execute("SELECT original_name FROM videos")]
    assert names == ["keep.mp4"]


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "twice.db"
    assert _run_migrate(db).returncode == 0
    assert _run_migrate(db).returncode == 0

    assert _tables(db) - {"alembic_version"} == _expected_tables()


def test_frame_timings_migration_is_idempotent(tmp_path: Path) -> None:
    """The frame_timings migration must adopt an existing table, not fail."""
    db = tmp_path / "preexisting.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}"}
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.core.database import init_models, SessionLocal\n"
                "from app.models import Video, FrameTimingRecord\n"
                "init_models()\n"
                "s = SessionLocal()\n"
                "s.add(Video(id='v1', original_name='a.mp4', filename='a.mp4',"
                " mime_type='video/mp4', size_bytes=1, status='uploaded'))\n"
                "s.commit()\n"
                "s.add(FrameTimingRecord(id='f1', video_id='v1', frame_id=1, elapsed_ms=5.0))\n"
                "s.commit()\n"
            ),
        ],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert _run_migrate(db).returncode == 0

    with sqlite3.connect(db) as conn:
        rows = [row[0] for row in conn.execute("SELECT id FROM frame_timings")]
    assert rows == ["f1"], "existing timings must not be dropped or recreated"


@pytest.mark.parametrize("revision", ["5d307872fa5b", "6e55088f8611"])
def test_partial_history_upgrades_forward(tmp_path: Path, revision: str) -> None:
    """A database stamped at an older revision must reach head."""
    db = tmp_path / f"{revision}.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db}"}
    subprocess.run(  # noqa: S603  (fixed argv: sys.executable + a parametrized revision id)
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    result = _run_migrate(db)

    assert result.returncode == 0, result.stderr
    assert _tables(db) - {"alembic_version"} == _expected_tables()
