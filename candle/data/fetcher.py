"""OHLCV fetcher — wraps ccxt to retrieve candle data from supported exchanges.

Handles NetworkError, ExchangeError, and RateLimitExceeded on every call.
Returns a normalized DataFrame; never returns raw ccxt responses.
"""

import pandas as pd
import ccxt.async_support as ccxt

from candle.data.normalizer import normalize


SUPPORTED_TIMEFRAMES: frozenset[str] = frozenset({"1h", "4h", "1d"})


async def fetch_ohlcv(
    exchange: ccxt.Exchange,
    symbol: str,
    timeframe: str,
    limit: int = 500,
) -> pd.DataFrame:
    """Fetch OHLCV candles for a symbol and return a normalized DataFrame.

    Args:
        exchange: An async ccxt Exchange instance (from exchange_factory).
        symbol: Trading pair symbol, e.g. "BTC/USDT".
        timeframe: Candle timeframe. Must be one of SUPPORTED_TIMEFRAMES.
        limit: Number of candles to fetch. Defaults to 500.

    Returns:
        DataFrame with columns: timestamp (UTC), open, high, low, close, volume.
        Timestamps are timezone-aware (UTC).

    Raises:
        ValueError: If timeframe is not in SUPPORTED_TIMEFRAMES.
        ccxt.NetworkError: On network-level failures (caller should retry).
        ccxt.ExchangeError: On exchange-level errors (caller should log and skip).
        ccxt.RateLimitExceeded: When the exchange rate limit is hit.
    """
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(
            f"unsupported timeframe '{timeframe}'. Must be one of {sorted(SUPPORTED_TIMEFRAMES)}"
        )

    raw = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    return normalize(raw)
