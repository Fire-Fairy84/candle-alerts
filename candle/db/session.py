"""Async SQLAlchemy engine and session factory.

All database access goes through get_session(). Never create engine or sessions
outside this module.
"""

import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from candle.config import settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

# Variable names to try, in priority order.
# CANDLE_DB_URL is the project-specific var; DATABASE_URL is the Railway default.
_DB_URL_VARS = (
    "CANDLE_DB_URL",
    "DATABASE_URL",
)


def _resolve_db_url() -> str:
    """Find the database URL from environment variables or pydantic-settings.

    Tries CANDLE_DB_URL then DATABASE_URL. Falls back to pydantic-settings
    (reads from .env in local dev). Skips empty strings.

    Returns:
        A postgresql+asyncpg:// connection URL.

    Raises:
        RuntimeError: If no database URL can be resolved.
    """
    for var in _DB_URL_VARS:
        url = os.environ.get(var, "")
        if url:
            logger.info("Database URL resolved (source: %s env var)", var)
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if settings.candle_db_url:
        logger.info("Database URL resolved (source: pydantic-settings .env)")
        return settings.candle_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    raise RuntimeError(
        "No database URL found. Set CANDLE_DB_URL or DATABASE_URL."
    )


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _resolve_db_url(),
            echo=not settings.is_production,
            pool_pre_ping=True,
        )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


def AsyncSessionFactory() -> AsyncSession:
    """Return a new async session from the lazily-initialised factory."""
    return _get_session_factory()()


async def dispose_engine() -> None:
    """Dispose the database engine connection pool.

    Called during application shutdown (FastAPI lifespan) to cleanly release
    all pooled connections. Safe to call when no engine has been initialised.
    """
    if _engine is not None:
        await _engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, closing it when the context exits.

    Usage::

        async with get_session() as session:
            result = await session.execute(...)

    Yields:
        An AsyncSession bound to the configured engine.
    """
    async with _get_session_factory()() as session:
        yield session
