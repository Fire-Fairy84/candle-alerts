"""Generate stable OHLCV fixtures for tests.

Downloads real BTC/USDT 4h candles from Binance (public endpoint, no API key needed)
and saves them as CSV files in tests/fixtures/.

Run once to create fixtures. Never regenerate automatically — fixtures must be
stable and committed to git.

Usage:
    python scripts/generate_fixtures.py
"""

import json
import sys
from pathlib import Path

import ccxt
import pandas as pd

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
SYMBOL = "BTC/USDT"
TIMEFRAME = "4h"
FETCH_LIMIT = 500  # fetch enough history to find clean signals


def _ewm(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("inf"))
    return 100 - (100 / (1 + rs))


def fetch_raw(exchange: ccxt.Exchange) -> list:
    print(f"Fetching {FETCH_LIMIT} × {TIMEFRAME} candles for {SYMBOL} from Binance…")
    raw = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=FETCH_LIMIT)
    print(f"  → received {len(raw)} candles")
    return raw


def raw_to_df(raw: list) -> pd.DataFrame:
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    numeric = ["open", "high", "low", "close", "volume"]
    df[numeric] = df[numeric].astype("float64")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def save_btc_4h_100(df: pd.DataFrame) -> None:
    """Save the most recent 100 candles as the general-purpose fixture."""
    out = df.tail(100).copy().reset_index(drop=True)
    path = FIXTURES_DIR / "btc_4h_100.csv"
    out.to_csv(path, index=False)
    print(f"  Saved {len(out)} candles → {path}")


def save_btc_4h_crossover(df: pd.DataFrame) -> None:
    """Find a window where EMA(9) crosses above EMA(21) on the last candle and save it."""
    fast, slow = 9, 21
    window = 60  # candles to include in the fixture (enough history for indicators)

    df = df.copy()
    df["ema_9"] = _ewm(df["close"], fast)
    df["ema_21"] = _ewm(df["close"], slow)

    # crossover: ema_9[i] >= ema_21[i] and ema_9[i-1] < ema_21[i-1]
    crossed = (df["ema_9"] >= df["ema_21"]) & (df["ema_9"].shift(1) < df["ema_21"].shift(1))

    # find the most recent crossover that has at least `window` candles before it
    candidates = df.index[crossed & (df.index >= window)]
    if candidates.empty:
        print("  WARNING: no EMA crossover found — falling back to last 60 candles")
        idx = len(df) - 1
    else:
        idx = int(candidates[-1])

    out = df.iloc[max(0, idx - window + 1) : idx + 1].copy()
    # drop computed columns — fixture contains only raw OHLCV
    out = out[["timestamp", "open", "high", "low", "close", "volume"]].reset_index(drop=True)

    path = FIXTURES_DIR / "btc_4h_crossover.csv"
    out.to_csv(path, index=False)
    print(f"  Saved {len(out)} candles (crossover at index {idx}) → {path}")


def save_btc_4h_overbought(df: pd.DataFrame) -> None:
    """Find a window ending where RSI > 70 on the last candle and save it."""
    window = 60
    period = 14

    df = df.copy()
    df["rsi"] = _rsi(df["close"], period)

    # find the most recent candle where RSI > 70 and has enough history
    overbought = df[(df["rsi"] > 70) & (df.index >= window)]
    if overbought.empty:
        print("  WARNING: no RSI > 70 found — falling back to last 60 candles")
        idx = len(df) - 1
    else:
        idx = int(overbought.index[-1])

    out = df.iloc[max(0, idx - window + 1) : idx + 1].copy()
    out = out[["timestamp", "open", "high", "low", "close", "volume"]].reset_index(drop=True)

    path = FIXTURES_DIR / "btc_4h_overbought.csv"
    out.to_csv(path, index=False)
    print(f"  Saved {len(out)} candles (RSI={df.loc[idx, 'rsi']:.1f} at last candle) → {path}")


def save_raw_ccxt_binance(raw: list) -> None:
    """Save the first 10 rows of the raw ccxt response for normalizer tests."""
    sample = raw[:10]
    path = FIXTURES_DIR / "raw_ccxt_binance.json"
    path.write_text(json.dumps(sample, indent=2))
    print(f"  Saved {len(sample)} raw rows → {path}")


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    exchange = ccxt.binance({"enableRateLimit": True})

    try:
        raw = fetch_raw(exchange)
    except ccxt.NetworkError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except ccxt.ExchangeError as e:
        print(f"Exchange error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        pass

    df = raw_to_df(raw)

    print("\nGenerating fixtures:")
    save_btc_4h_100(df)
    save_btc_4h_crossover(df)
    save_btc_4h_overbought(df)
    save_raw_ccxt_binance(raw)

    print("\nDone. Commit tests/fixtures/ to git.")


if __name__ == "__main__":
    main()
