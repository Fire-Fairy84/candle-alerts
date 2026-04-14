"""Shared pytest fixtures for all test modules.

Provides:
- An async test database session backed by a real PostgreSQL instance.
- A mock ccxt exchange that returns fixture data without hitting any real API.
- A mock Telegram client for verifying alert delivery without sending real messages.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from candle.config import settings
from candle.db.models import Base


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create the test database schema once per session, drop it on teardown."""
    engine = create_async_engine(settings.candle_db_url_test, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Yield a transactional test session that rolls back after each test."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
def mock_exchange(mocker):
    """Return a mock ccxt async exchange that never calls any real API."""
    exchange = mocker.AsyncMock()
    exchange.id = "binance"
    return exchange


@pytest.fixture
def mock_telegram(mocker):
    """Return a mock Telegram bot that captures sent messages without delivering them."""
    return mocker.AsyncMock()
