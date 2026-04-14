"""Screener condition primitives.

Each condition takes a DataFrame (with computed indicators) and returns a bool
indicating whether the condition is met on the latest candle.

Conditions are pure functions — no I/O, no side effects.
"""

import pandas as pd


def ema_crossover(df: pd.DataFrame, fast: int, slow: int) -> bool:
    """Return True if the fast EMA crossed above the slow EMA on the last candle.

    A crossover is detected when fast EMA was below slow EMA on the previous
    candle and is at or above slow EMA on the current candle.

    Args:
        df: DataFrame with pre-computed EMA columns named f"ema_{fast}" and
            f"ema_{slow}". Must have at least 2 rows.
        fast: Fast EMA period (used to look up the column name).
        slow: Slow EMA period (used to look up the column name).

    Returns:
        True if a crossover occurred, False otherwise.

    Raises:
        KeyError: If the expected EMA columns are not present in df.
        ValueError: If df has fewer than 2 rows.
    """
    if len(df) < 2:
        raise ValueError(f"ema_crossover requires at least 2 rows, got {len(df)}")

    fast_col = f"ema_{fast}"
    slow_col = f"ema_{slow}"

    for col in (fast_col, slow_col):
        if col not in df.columns:
            raise KeyError(f"column '{col}' not found in DataFrame")

    prev_fast = df[fast_col].iloc[-2]
    prev_slow = df[slow_col].iloc[-2]
    last_fast = df[fast_col].iloc[-1]
    last_slow = df[slow_col].iloc[-1]

    return bool(prev_fast < prev_slow and last_fast >= last_slow)


def ema_trending(df: pd.DataFrame, fast: int, slow: int) -> bool:
    """Return True if the fast EMA is above the slow EMA on the latest candle.

    Unlike ema_crossover (which detects the exact transition), this condition
    fires as long as the trend persists — making it a state-based check.

    Args:
        df: DataFrame with pre-computed EMA columns named f"ema_{fast}" and
            f"ema_{slow}". Must have at least 1 row.
        fast: Fast EMA period (used to look up the column name).
        slow: Slow EMA period (used to look up the column name).

    Returns:
        True if fast EMA > slow EMA on the last row, False otherwise.

    Raises:
        KeyError: If the expected EMA columns are not present in df.
    """
    fast_col = f"ema_{fast}"
    slow_col = f"ema_{slow}"

    for col in (fast_col, slow_col):
        if col not in df.columns:
            raise KeyError(f"column '{col}' not found in DataFrame")

    return bool(df[fast_col].iloc[-1] > df[slow_col].iloc[-1])


def rsi_range(df: pd.DataFrame, min_val: float, max_val: float) -> bool:
    """Return True if the RSI of the latest candle is within [min_val, max_val].

    Args:
        df: DataFrame with a pre-computed "rsi" column.
        min_val: Lower bound (inclusive).
        max_val: Upper bound (inclusive).

    Returns:
        True if RSI is within range, False otherwise.

    Raises:
        KeyError: If "rsi" column is not present in df.
    """
    if "rsi" not in df.columns:
        raise KeyError("column 'rsi' not found in DataFrame")

    return bool(min_val <= df["rsi"].iloc[-1] <= max_val)


def price_above_vwap(df: pd.DataFrame) -> bool:
    """Return True if the close price of the latest candle is above VWAP.

    Args:
        df: DataFrame with pre-computed "vwap" column and a "close" column.

    Returns:
        True if close > vwap on the last row, False otherwise.

    Raises:
        KeyError: If "close" or "vwap" columns are not present in df.
    """
    for col in ("close", "vwap"):
        if col not in df.columns:
            raise KeyError(f"column '{col}' not found in DataFrame")

    return bool(df["close"].iloc[-1] > df["vwap"].iloc[-1])


def volume_spike(df: pd.DataFrame, multiplier: float, window: int = 20) -> bool:
    """Return True if the latest candle's volume exceeds the rolling average by multiplier.

    The rolling average is computed over the `window` candles preceding the
    current one (no look-ahead bias — the current candle is excluded).

    Args:
        df: DataFrame with a "volume" column.
        multiplier: Factor above the rolling average to trigger. E.g. 2.0 means
                    volume must be at least 2× the rolling mean.
        window: Rolling window size in candles. Defaults to 20.

    Returns:
        True if volume[-1] >= rolling_mean * multiplier, False otherwise.

    Raises:
        KeyError: If "volume" column is not present in df.
        ValueError: If df has fewer than window + 1 rows.
    """
    if "volume" not in df.columns:
        raise KeyError("column 'volume' not found in DataFrame")

    if len(df) < window + 1:
        raise ValueError(
            f"volume_spike requires at least {window + 1} rows (window={window}), got {len(df)}"
        )

    rolling_mean = df["volume"].iloc[-(window + 1):-1].mean()
    return bool(df["volume"].iloc[-1] >= rolling_mean * multiplier)
