"""Database engine and session management.

Uses SQLAlchemy 2.0 with a declarative base. The connection URL comes from
``settings.database_url`` — SQLite for local development, PostgreSQL in
production (set ``DATABASE_URL`` accordingly).
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _configure_sqlite_pragmas(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    del connection_record
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def create_db_engine(url: str | None = None):
    """Create a configured SQLAlchemy engine, enabling SQLite pragmas when needed."""
    url = url or settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _configure_sqlite_pragmas)
    return engine


engine = create_db_engine()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_models() -> None:
    """Import all models and create tables (used for non-migrated environments)."""
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
