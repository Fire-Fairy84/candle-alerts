"""Tests for candle.data.bit2me — Bit2Me exchange client."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import ccxt.async_support as ccxt
import httpx
import pytest

from candle.data.bit2me import Bit2MeExchange
from candle.data.normalizer import normalize


RAW_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "raw_bit2me_btc_eur.json").read_text()
)


@pytest.fixture
def bit2me() -> Bit2MeExchange:
    return Bit2MeExchange()


def _mock_response(status_code: int = 200, json_data: list | dict | None = None) -> httpx.Response:
    """Build a fake httpx.Response."""
    resp = httpx.Response(
        status_code=status_code,
        json=json_data if json_data is not None else RAW_FIXTURE,
        request=httpx.Request("GET", "https://gateway.bit2me.com/v1/trading/candle"),
    )
    return resp


class TestBit2MeFetchOhlcv:
    async def test_returns_list_of_lists(self, bit2me):
        """fetch_ohlcv must return raw OHLCV data in ccxt-compatible format."""
        bit2me._client = AsyncMock()
        bit2me._client.get = AsyncMock(return_value=_mock_response())

        data = await bit2me.fetch_ohlcv("BTC/EUR", "4h")

        assert isinstance(data, list)
        assert len(data) == len(RAW_FIXTURE)
        assert len(data[0]) == 6

    async def test_passes_correct_params(self, bit2me):
        """API call must use the mapped interval and capped limit."""
        bit2me._client = AsyncMock()
        bit2me._client.get = AsyncMock(return_value=_mock_response())

        await bit2me.fetch_ohlcv("BTC/EUR", "4h", limit=500)

        bit2me._client.get.assert_called_once_with(
            "/v1/trading/candle",
            params={"symbol": "BTC/EUR", "interval": "240", "limit": 288},
        )

    async def test_timeframe_mapping(self, bit2me):
        """All supported timeframes must map to Bit2Me intervals."""
        bit2me._client = AsyncMock()
        bit2me._client.get = AsyncMock(return_value=_mock_response())

        for tf, expected in [("1h", "60"), ("4h", "240"), ("1d", "1440")]:
            bit2me._client.get.reset_mock()
            await bit2me.fetch_ohlcv("BTC/EUR", tf)
            call_params = bit2me._client.get.call_args.kwargs["params"]
            assert call_params["interval"] == expected, f"timeframe {tf}"

    async def test_unsupported_timeframe_raises(self, bit2me):
        """Unsupported timeframes must raise ccxt.ExchangeError."""
        with pytest.raises(ccxt.ExchangeError, match="unsupported timeframe"):
            await bit2me.fetch_ohlcv("BTC/EUR", "15m")

    async def test_rate_limit_429_raises(self, bit2me):
        """HTTP 429 must raise ccxt.RateLimitExceeded."""
        bit2me._client = AsyncMock()
        bit2me._client.get = AsyncMock(return_value=_mock_response(429))

        with pytest.raises(ccxt.RateLimitExceeded):
            await bit2me.fetch_ohlcv("BTC/EUR", "4h")

    async def test_api_error_raises(self, bit2me):
        """Non-200 responses must raise ccxt.ExchangeError."""
        bit2me._client = AsyncMock()
        bit2me._client.get = AsyncMock(
            return_value=_mock_response(400, {"error": "Bad Request"})
        )

        with pytest.raises(ccxt.ExchangeError, match="400"):
            await bit2me.fetch_ohlcv("BTC/EUR", "4h")

    async def test_network_error_raises(self, bit2me):
        """httpx transport errors must raise ccxt.NetworkError."""
        bit2me._client = AsyncMock()
        bit2me._client.get = AsyncMock(side_effect=httpx.ConnectError("dns failed"))

        with pytest.raises(ccxt.NetworkError, match="network error"):
            await bit2me.fetch_ohlcv("BTC/EUR", "4h")

    async def test_compatible_with_normalizer(self, bit2me):
        """Bit2Me response must be normalizable by the standard normalizer."""
        bit2me._client = AsyncMock()
        bit2me._client.get = AsyncMock(return_value=_mock_response())

        data = await bit2me.fetch_ohlcv("BTC/EUR", "4h")
        df = normalize(data)

        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert len(df) == len(RAW_FIXTURE)
        assert str(df["timestamp"].dt.tz) == "UTC"

    async def test_close_calls_aclose(self, bit2me):
        """close() must close the underlying httpx client."""
        bit2me._client = AsyncMock()
        await bit2me.close()
        bit2me._client.aclose.assert_called_once()


class TestBit2MeInFactory:
    def test_build_exchange_returns_bit2me_instance(self):
        """build_exchange('bit2me', ...) must return a Bit2MeExchange."""
        from candle.config import Settings
        from candle.data.exchange_factory import build_exchange

        settings = Settings(candle_db_url="postgresql+asyncpg://x:x@localhost/x")
        exchange = build_exchange("bit2me", settings)
        assert isinstance(exchange, Bit2MeExchange)
        assert exchange.id == "bit2me"
