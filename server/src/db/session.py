from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncIterator

import asyncpg
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from ..config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_init_lock = asyncio.Lock()
_initialized = False


def _get_database_url() -> str:
    dsn = get_settings().pg_dsn
    if dsn is None:
        raise RuntimeError(
            "PG_DSN is not configured. Set PG_DSN or DATABASE_URL to a PostgreSQL async URL. "
            "When running in Docker, remember that localhost points to the container itself."
        )
    return dsn.unicode_string()


def _get_database_target() -> URL:
    return make_url(_get_database_url())


def _to_asyncpg_dsn(url: URL) -> str:
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _get_database_url(),
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def ensure_database_exists() -> bool:
    settings = get_settings()
    target_url = _get_database_target()
    target_db = target_url.database
    if not target_db:
        raise RuntimeError("PG_DSN must include a database name.")

    admin_url = target_url.set(database=settings.pg_admin_db)
    connection = await asyncpg.connect(dsn=_to_asyncpg_dsn(admin_url))
    try:
        database_exists = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            target_db,
        )
        if database_exists:
            return False

        quoted_database = '"' + target_db.replace('"', '""') + '"'
        try:
            await connection.execute(f"CREATE DATABASE {quoted_database}")
        except asyncpg.exceptions.DuplicateDatabaseError:
            return False
        return True
    finally:
        await connection.close()


def _build_alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    config.set_main_option("sqlalchemy.url", _get_database_url())
    return config


def _run_migrations() -> None:
    command.upgrade(_build_alembic_config(), "head")


async def run_migrations() -> None:
    await asyncio.to_thread(_run_migrations)


async def initialize_database() -> None:
    global _initialized

    if _initialized:
        return

    async with _init_lock:
        if _initialized:
            return

        await ensure_database_exists()
        await run_migrations()
        get_engine()
        get_session_factory()
        _initialized = True
