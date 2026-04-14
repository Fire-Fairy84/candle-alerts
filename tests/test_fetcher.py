"""Tests for candle.data.fetcher and candle.data.exchange_factory."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import ccxt.async_support as ccxt

from candle.data.fetcher import fetch_ohlcv, SUPPORTED_TIMEFRAMES
from candle.data.exchange_factory import build_exchange, SUPPORTED_EXCHANGES
from candle.config import Settings


RAW_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "raw_ccxt_binance.json").read_text()
)

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_exchange() -> AsyncMock:
    """Async mock exchange that returns the Binance fixture by default."""
    exchange = AsyncMock(spec=ccxt.Exchange)
    exchange.fetch_ohlcv = AsyncMock(return_value=RAW_FIXTURE)
    return exchange


@pytest.fixture
def mock_settings() -> Settings:
    """Settings instance with no API keys (public access only)."""
    return Settings(
        database_url="postgresql+asyncpg://x:x@localhost/x",
        binance_api_key="",
        binance_api_secret="",
        kraken_api_key="",
        kraken_api_secret="",
        coinbase_api_key="",
        coinbase_api_secret="",
    )


@pytest.fixture
def mock_settings_with_keys() -> Settings:
    """Settings instance with API keys present."""
    return Settings(
        database_url="postgresql+asyncpg://x:x@localhost/x",
        binance_api_key="test_key",
        binance_api_secret="test_secret",
        kraken_api_key="",
        kraken_api_secret="",
        coinbase_api_key="",
        coinbase_api_secret="",
    )


# ---------------------------------------------------------------------------
# fetch_ohlcv
# ---------------------------------------------------------------------------

class TestFetchOhlcv:
    async def test_returns_dataframe_with_expected_columns(self, mock_exchange):
        df = await fetch_ohlcv(mock_exchange, "BTC/USDT", "4h")
        assert list(df.columns) == OHLCV_COLUMNS

    async def test_timestamps_are_utc(self, mock_exchange):
        df = await fetch_ohlcv(mock_exchange, "BTC/USDT", "4h")
        assert str(df["timestamp"].dt.tz) == "UTC"

    async def test_raises_on_unsupported_timeframe(self, mock_exchange):
        with pytest.raises(ValueError, match="unsupported timeframe"):
            await fetch_ohlcv(mock_exchange, "BTC/USDT", "15m")

    async def test_unsupported_timeframe_does_not_call_exchange(self, mock_exchange):
        with pytest.raises(ValueError):
            await fetch_ohlcv(mock_exchange, "BTC/USDT", "15m")
        mock_exchange.fetch_ohlcv.assert_not_called()

    async def test_propagates_network_error(self, mock_exchange):
        mock_exchange.fetch_ohlcv.side_effect = ccxt.NetworkError("timeout")
        with pytest.raises(ccxt.NetworkError):
            await fetch_ohlcv(mock_exchange, "BTC/USDT", "4h")

    async def test_propagates_rate_limit_exceeded(self, mock_exchange):
        mock_exchange.fetch_ohlcv.side_effect = ccxt.RateLimitExceeded("rate limit")
        with pytest.raises(ccxt.RateLimitExceeded):
            await fetch_ohlcv(mock_exchange, "BTC/USDT", "4h")

    async def test_propagates_exchange_error(self, mock_exchange):
        mock_exchange.fetch_ohlcv.side_effect = ccxt.ExchangeError("bad symbol")
        with pytest.raises(ccxt.ExchangeError):
            await fetch_ohlcv(mock_exchange, "BTC/USDT", "4h")

    async def test_calls_exchange_with_correct_arguments(self, mock_exchange):
        await fetch_ohlcv(mock_exchange, "ETH/USDT", "1d", limit=100)
        mock_exchange.fetch_ohlcv.assert_called_once_with("ETH/USDT", "1d", limit=100)

    async def test_all_supported_timeframes_are_accepted(self, mock_exchange):
        for tf in SUPPORTED_TIMEFRAMES:
            mock_exchange.fetch_ohlcv.reset_mock(return_value=True)
            mock_exchange.fetch_ohlcv.return_value = RAW_FIXTURE
            df = await fetch_ohlcv(mock_exchange, "BTC/USDT", tf)
            assert list(df.columns) == OHLCV_COLUMNS


# ---------------------------------------------------------------------------
# build_exchange
# ---------------------------------------------------------------------------

class TestBuildExchange:
    def test_raises_on_unsupported_slug(self, mock_settings):
        with pytest.raises(ValueError, match="unsupported exchange"):
            build_exchange("bitmex", mock_settings)

    def test_all_supported_slugs_return_exchange(self, mock_settings):
        from candle.data.bit2me import Bit2MeExchange

        for slug in SUPPORTED_EXCHANGES:
            exchange = build_exchange(slug, mock_settings)
            assert isinstance(exchange, (ccxt.Exchange, Bit2MeExchange))

    def test_rate_limit_is_enabled(self, mock_settings):
        exchange = build_exchange("binance", mock_settings)
        assert exchange.enableRateLimit is True

    def test_no_api_key_set_when_settings_empty(self, mock_settings):
        exchange = build_exchange("binance", mock_settings)
        assert not exchange.apiKey

    def test_api_key_set_when_settings_present(self, mock_settings_with_keys):
        exchange = build_exchange("binance", mock_settings_with_keys)
        assert exchange.apiKey == "test_key"
        assert exchange.secret == "test_secret"

    def test_returns_async_exchange_instance(self, mock_settings):
        exchange = build_exchange("binance", mock_settings)
        # ccxt async exchanges have a fetch_ohlcv coroutine
        import inspect
        assert inspect.iscoroutinefunction(exchange.fetch_ohlcv)
