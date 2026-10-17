"""Database engine and session helpers.

The API uses PostgreSQL in Docker (``postgresql+psycopg``), while still
allowing a SQLite URL for quick local tests.  The URL is read at import time
so every process uses the same configured database.
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _database_url() -> str:
    configured = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://pulse:pulse_dev_password@postgres:5432/pulse_crm",
    ).strip()
    # Some managed Postgres providers still expose the old postgres:// form.
    if configured.startswith("postgres://"):
        return "postgresql+psycopg://" + configured.removeprefix("postgres://")
    if configured.startswith("postgresql://"):
        return "postgresql+psycopg://" + configured.removeprefix("postgresql://")
    return configured


DATABASE_URL = _database_url()
_engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    # SQLite is useful for local smoke checks; it is not used by Compose.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

