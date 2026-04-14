"""Volume indicators: VWAP, OBV, CVD."""

import pandas as pd


def vwap(df: pd.DataFrame) -> pd.Series:
    """Compute Volume-Weighted Average Price.

    Calculated as cumulative (typical_price * volume) / cumulative volume,
    where typical_price = (high + low + close) / 3.

    Args:
        df: OHLCV DataFrame with "high", "low", "close", and "volume" columns.

    Returns:
        Series of VWAP values, aligned with df index. No NaN values.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    return (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()


def obv(df: pd.DataFrame) -> pd.Series:
    """Compute On-Balance Volume.

    Args:
        df: OHLCV DataFrame with "close" and "volume" columns.

    Returns:
        Series of cumulative OBV values, aligned with df index.
    """
    direction = df["close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    direction.iloc[0] = 0
    return (direction * df["volume"]).cumsum()


def cvd(df: pd.DataFrame) -> pd.Series:
    """Compute Cumulative Volume Delta (approximation via close vs open).

    Positive delta when close > open (buying pressure),
    negative when close < open (selling pressure).

    Args:
        df: OHLCV DataFrame with "open", "close", and "volume" columns.

    Returns:
        Series of cumulative volume delta values, aligned with df index.
    """
    delta = df["close"] - df["open"]
    direction = delta.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * df["volume"]).cumsum()
