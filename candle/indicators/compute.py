"""Shared indicator computation used by the scheduler and the API.

Single source of truth for which indicators are computed and what their
column names are. Both fetch/screen cycles and the candles API route use this.
"""

import pandas as pd

from candle.indicators.momentum import rsi
from candle.indicators.trend import ema
from candle.indicators.volume import vwap


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all standard indicator columns to a candle DataFrame in-place.

    Computes EMA 9, 21, 50, 200; RSI(14); and VWAP. Column names are
    canonical: ``ema_9``, ``ema_21``, ``ema_50``, ``ema_200``, ``rsi``, ``vwap``.

    Args:
        df: OHLCV DataFrame with open, high, low, close, volume columns.

    Returns:
        The same DataFrame with indicator columns added.
    """
    df["ema_9"] = ema(df, 9)
    df["ema_21"] = ema(df, 21)
    df["ema_50"] = ema(df, 50)
    df["ema_200"] = ema(df, 200)
    df["rsi"] = rsi(df)
    df["vwap"] = vwap(df)
    return df
