"""Momentum indicators: RSI, Stochastic."""

import pandas as pd


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute Relative Strength Index.

    Uses Wilder smoothing (EWM with com=period-1) to match the standard RSI
    definition. Leading values are NaN until enough data is available.

    Args:
        df: OHLCV DataFrame with a "close" column.
        period: Lookback period in candles. Defaults to 14.

    Returns:
        Series of RSI values (0–100), aligned with df index.
        Leading values are NaN for the first `period` rows.
    """
    delta = df["close"].diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, min_periods=period).mean()
    rs = gain / loss.replace(0, float("inf"))
    return 100 - (100 / (1 + rs))


def stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
) -> pd.DataFrame:
    """Compute Stochastic Oscillator (%K and %D lines).

    %K = (close - lowest_low) / (highest_high - lowest_low) * 100
    %D = SMA(%K, d_period)

    Args:
        df: OHLCV DataFrame with "high", "low", and "close" columns.
        k_period: %K lookback period. Defaults to 14.
        d_period: %D smoothing period. Defaults to 3.

    Returns:
        DataFrame with columns: stoch_k, stoch_d.
        Values range 0–100. Leading values are NaN.
    """
    lowest_low = df["low"].rolling(window=k_period).min()
    highest_high = df["high"].rolling(window=k_period).max()
    stoch_k = (df["close"] - lowest_low) / (highest_high - lowest_low) * 100
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return pd.DataFrame({"stoch_k": stoch_k, "stoch_d": stoch_d}, index=df.index)
