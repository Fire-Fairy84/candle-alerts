"""Bit2Me exchange client with a ccxt-compatible interface.

Bit2Me is not supported by ccxt, so this module provides a lightweight async
client that implements the same ``fetch_ohlcv`` / ``close`` contract used by
the rest of the data layer.

API docs: https://api.bit2me.com/trading-spot-rest
Rate limit: 2 requests/second on the candle endpoint.
Max candles per request: 288.
"""

import asyncio
import logging
from typing import Any

import ccxt.async_support as ccxt
import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://gateway.bit2me.com"

_TIMEFRAME_MAP: dict[str, str] = {
    "1h": "60",
    "4h": "240",
    "1d": "1440",
}

_MAX_CANDLES = 288


class Bit2MeExchange:
    """Async Bit2Me client that quacks like a ccxt exchange.

    Only implements the subset of the ccxt interface that Candle uses:
    ``fetch_ohlcv`` and ``close``.  Raises standard ccxt exceptions so that
    ``fetch_job`` error handling works without changes.
    """

    id: str = "bit2me"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=_BASE_URL, timeout=30.0)
        self._last_request_at: float = 0.0

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = _MAX_CANDLES,
        **_kwargs: Any,
    ) -> list[list[Any]]:
        """Fetch OHLCV candles from Bit2Me.

        Args:
            symbol: Trading pair, e.g. ``"BTC/EUR"``.
            timeframe: One of ``"1h"``, ``"4h"``, ``"1d"``.
            limit: Max candles to return (capped at 288).

        Returns:
            List of ``[timestamp_ms, open, high, low, close, volume]`` rows,
            identical to the ccxt format.

        Raises:
            ccxt.ExchangeError: On API-level errors or unsupported timeframe.
            ccxt.NetworkError: On HTTP transport failures.
            ccxt.RateLimitExceeded: When the 2 req/s limit is hit.
        """
        interval = _TIMEFRAME_MAP.get(timeframe)
        if interval is None:
            raise ccxt.ExchangeError(
                f"Bit2Me: unsupported timeframe '{timeframe}'. "
                f"Supported: {sorted(_TIMEFRAME_MAP.keys())}"
            )

        await self._throttle()

        try:
            response = await self._client.get(
                "/v1/trading/candle",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": min(limit, _MAX_CANDLES),
                },
            )
            self._last_request_at = asyncio.get_event_loop().time()
        except httpx.HTTPError as exc:
            raise ccxt.NetworkError(f"Bit2Me network error: {exc}") from exc

        if response.status_code == 429:
            raise ccxt.RateLimitExceeded("Bit2Me rate limit exceeded")
        if response.status_code != 200:
            raise ccxt.ExchangeError(
                f"Bit2Me API error {response.status_code}: {response.text}"
            )

        data = response.json()
        if not isinstance(data, list):
            raise ccxt.ExchangeError(
                f"Bit2Me: unexpected response format: {type(data).__name__}"
            )
        return data

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _throttle(self) -> None:
        """Enforce the 2 req/s rate limit (0.5 s between requests)."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_at
        if elapsed < 0.5:
            await asyncio.sleep(0.5 - elapsed)
