"""Database engine and session management.

Uses SQLAlchemy so the same models work on SQLite (default, offline) and
PostgreSQL (via ``ADAPTIVE_DATABASE_URL``). No code changes needed to switch.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False for FastAPI's threadpool; harmless for PG.
_connect_args = {}
if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables, then apply additive column migrations.

    We deliberately use ``create_all`` (no migration framework) for simplicity.
    To stay robust when new columns are added to existing prototype databases,
    ``_auto_add_missing_columns`` performs additive-only ALTER TABLE statements.
    """
    from . import models  # noqa: F401  (registers all tables on Base.metadata)

    Base.metadata.create_all(bind=engine)
    _auto_add_missing_columns()


def _auto_add_missing_columns() -> None:
    """Additive-only migration: add columns present in models but missing in DB."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                coltype = col.type.compile(engine.dialect)
                ddl = f'ALTER TABLE {table.name} ADD COLUMN {col.name} {coltype}'
                default = getattr(col.default, "arg", None)
                if isinstance(default, bool):
                    ddl += f" DEFAULT {1 if default else 0}"
                elif isinstance(default, (int, float)):
                    ddl += f" DEFAULT {default}"
                elif isinstance(default, str):
                    ddl += f" DEFAULT '{default}'"
                try:
                    conn.execute(text(ddl))
                except Exception:  # noqa: BLE001 - best-effort additive migration
                    pass
