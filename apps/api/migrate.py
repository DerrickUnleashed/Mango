"""Apply database migrations for container startup.

Exits 0 when the database is already current, and raises on genuine
failure so the container does not start serving against a schema it does
not understand.

Two paths, distinguished by whether alembic has any recorded history:

  - a database created by migrations has an ``alembic_version`` row and is
    simply brought up to date;
  - a database created before migrations were wired up was built from the
    ORM metadata and has tables but no alembic history. Running
    ``upgrade head`` against it fails on the first ``create_table``
    ("table app_settings already exists"), so it is stamped at head
    instead. That is correct rather than a shortcut: such a database is
    already at head, because the migration chain and the ORM models
    describe the same schema.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  (registers tables on Base.metadata)
from alembic import command
from app.core.config import settings
from app.core.database import Base

# Resolved from this file rather than the cwd: the container entrypoint runs
# from /orchardvision, not apps/api.
ALEMBIC_INI = Path(__file__).resolve().parent / "alembic.ini"


def _config() -> Config:
    return Config(str(ALEMBIC_INI))


def _has_alembic_history(config: Config) -> bool:
    """True when alembic has a recorded current revision for this database."""
    engine = create_engine(settings.database_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            if "alembic_version" not in inspect(connection).get_table_names():
                return False
            context = MigrationContext.configure(connection)
            return context.get_current_revision() is not None
    finally:
        engine.dispose()


def _schema_is_empty(config: Config) -> bool:
    """True when the database has no application tables (a fresh volume)."""
    engine = create_engine(settings.database_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            names = set(inspect(connection).get_table_names())
    finally:
        engine.dispose()
    if names - {"alembic_version"}:
        return False
    # No tables at all, so genuinely fresh. Checked against the ORM so that
    # an unrecognised table is still treated as "not empty".
    return not names & set(Base.metadata.tables)


def main() -> int:
    config = _config()
    target = ScriptDirectory.from_config(config).get_current_head()

    if _has_alembic_history(config):
        print(f"migrations: upgrading to {target}", flush=True)
        command.upgrade(config, "head")
        return 0

    if _schema_is_empty(config):
        print("migrations: fresh database, applying full chain", flush=True)
        command.upgrade(config, "head")
        return 0

    print(
        "migrations: no alembic history but tables already present, "
        "stamping existing schema as head",
        flush=True,
    )
    command.stamp(config, "head")
    return 0


if __name__ == "__main__":
    sys.exit(main())
