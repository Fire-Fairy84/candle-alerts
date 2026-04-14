"""Normalizer — converts raw ccxt OHLCV responses into clean, typed DataFrames.

This module has no knowledge of exchanges or the database. Input in, DataFrame out.
"""

from typing import Any

import pandas as pd


RawOHLCV = list[list[Any]]  # ccxt returns [[timestamp_ms, o, h, l, c, v], ...]

OHLCV_COLUMNS: list[str] = ["timestamp", "open", "high", "low", "close", "volume"]


def normalize(raw: RawOHLCV) -> pd.DataFrame:
    """Convert a raw ccxt OHLCV list into a clean DataFrame.

    Args:
        raw: Raw output from ccxt's fetch_ohlcv — a list of
             [timestamp_ms, open, high, low, close, volume] rows.

    Returns:
        DataFrame with columns [timestamp, open, high, low, close, volume].
        - timestamp is UTC-aware datetime.
        - Numeric columns are float64.
        - Rows are sorted ascending by timestamp.
        - No duplicate timestamps.

    Raises:
        ValueError: If raw is empty or has an unexpected column count.
    """
    if not raw:
        raise ValueError("raw OHLCV data is empty")

    if any(len(row) != 6 for row in raw):
        raise ValueError(
            f"each OHLCV row must have exactly 6 columns, got rows with "
            f"{set(len(r) for r in raw)}"
        )

    df = pd.DataFrame(raw, columns=OHLCV_COLUMNS)

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].astype("float64")

    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    return df
