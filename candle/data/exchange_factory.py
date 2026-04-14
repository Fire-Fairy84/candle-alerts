"""Factory for building read-only exchange instances from application config.

Supports ccxt exchanges (Binance, Kraken, Coinbase) and custom connectors
(Bit2Me) behind a unified interface.
"""

from typing import Any

import ccxt.async_support as ccxt

from candle.config import Settings
from candle.data.bit2me import Bit2MeExchange


SUPPORTED_EXCHANGES: frozenset[str] = frozenset({"binance", "kraken", "coinbase", "bit2me"})


def build_exchange(slug: str, settings: Settings) -> Any:
    """Return a configured, read-only async exchange instance.

    For ccxt-supported exchanges, returns a ccxt Exchange with optional
    credentials from settings. For Bit2Me, returns a custom Bit2MeExchange
    that implements the same ``fetch_ohlcv`` / ``close`` contract.

    Args:
        slug: Exchange identifier. Must be one of SUPPORTED_EXCHANGES.
        settings: Application settings containing optional API credentials.

    Returns:
        An async exchange instance with ``fetch_ohlcv`` and ``close`` methods.

    Raises:
        ValueError: If slug is not in SUPPORTED_EXCHANGES.
    """
    if slug not in SUPPORTED_EXCHANGES:
        raise ValueError(
            f"unsupported exchange '{slug}'. Must be one of {sorted(SUPPORTED_EXCHANGES)}"
        )

    if slug == "bit2me":
        return Bit2MeExchange()

    exchange_class: type[ccxt.Exchange] = getattr(ccxt, slug)
    return exchange_class({"enableRateLimit": True, **_credentials(slug, settings)})


def _credentials(slug: str, settings: Settings) -> dict[str, str]:
    """Extract non-empty API credentials for the given exchange slug."""
    key_map: dict[str, tuple[str, str]] = {
        "binance": (settings.binance_api_key, settings.binance_api_secret),
        "kraken": (settings.kraken_api_key, settings.kraken_api_secret),
        "coinbase": (settings.coinbase_api_key, settings.coinbase_api_secret),
    }
    api_key, api_secret = key_map[slug]
    result: dict[str, str] = {}
    if api_key:
        result["apiKey"] = api_key
    if api_secret:
        result["secret"] = api_secret
    return result
