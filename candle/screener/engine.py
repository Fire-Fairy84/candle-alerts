"""Screener engine — evaluates a list of rules against indicator output.

The engine is stateless. It receives DataFrames and rules, and returns matches.
It has no knowledge of the database or the alert delivery layer.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from candle.screener.rules import Rule


@dataclass
class RuleMatch:
    """Represents a rule that fired on a specific symbol.

    Attributes:
        rule: The Rule that was triggered.
        symbol: Trading pair symbol that triggered the rule, e.g. "BTC/USDT".
        timeframe: Candle timeframe that was evaluated, e.g. "4h".
        message: Concise signal line stored in the DB and shown in Telegram.
        exchange_slug: Exchange where the pair is listed, e.g. "binance".
        candle_timestamp: UTC timestamp of the candle that triggered the rule.
        indicators: Key indicator values for the rule that fired, used in formatting.
    """

    rule: Rule
    symbol: str
    timeframe: str
    message: str
    exchange_slug: str = ""
    candle_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    indicators: dict[str, float] = field(default_factory=dict)


# Short, actionable signal lines. Volume Spike direction is computed in _build_signal.
_SIGNAL_TEMPLATES: dict[str, str] = {
    "EMA Crossover 9/21": "EMA crossover (9 > 21) — Bullish",
    "EMA Trending 9/21": "EMA 9 > EMA 21 — Bullish trend",
    "RSI Oversold": "RSI oversold — Bearish bias",
    "RSI Overbought": "RSI overbought — Bullish momentum",
    "Price Above VWAP": "Price above VWAP — Bullish bias",
}


def _extract_indicators(rule_name: str, df: pd.DataFrame) -> dict[str, float]:
    """Extract the indicator values relevant to the rule that fired.

    Only includes values actually used by the rule — no noise.

    Args:
        rule_name: Name of the rule that fired.
        df: DataFrame with OHLCV and indicator columns.

    Returns:
        Dict of indicator name → value for the last candle.
    """
    last = df.iloc[-1]
    close = float(last["close"]) if "close" in df.columns else 0.0

    if rule_name in ("EMA Crossover 9/21", "EMA Trending 9/21"):
        return {
            "close": close,
            "ema_9": float(last["ema_9"]),
            "ema_21": float(last["ema_21"]),
        }
    if rule_name in ("RSI Oversold", "RSI Overbought"):
        return {
            "close": close,
            "rsi": float(last["rsi"]),
        }
    if rule_name == "Price Above VWAP":
        return {
            "close": close,
            "vwap": float(last["vwap"]),
        }
    if rule_name == "Volume Spike 2x" and len(df) > 20:
        rolling_mean = df["volume"].iloc[-21:-1].mean()
        ratio = float(last["volume"] / rolling_mean) if rolling_mean > 0 else 0.0
        return {
            "close": close,
            "open": float(last["open"]) if "open" in df.columns else close,
            "volume": float(last["volume"]),
            "avg_volume": float(rolling_mean),
            "ratio": ratio,
        }
    return {"close": close}


def _build_signal(rule_name: str, indicators: dict[str, float]) -> str:
    """Build the concise signal line from the template and extracted indicator values.

    Volume Spike direction is determined by comparing close vs open on the triggering
    candle. Falls back to the rule name if no template is defined.

    Args:
        rule_name: Name of the rule that fired.
        indicators: Dict of indicator values extracted by _extract_indicators.

    Returns:
        Formatted signal line string.
    """
    if rule_name == "Volume Spike 2x":
        direction = "Bullish" if indicators.get("close", 0) >= indicators.get("open", 0) else "Bearish"
        ratio = indicators.get("ratio", 0.0)
        return f"Volume spike ({ratio:.1f}\u00d7) — {direction}"

    template = _SIGNAL_TEMPLATES.get(rule_name)
    if template is None:
        return rule_name
    try:
        return template.format(**indicators)
    except KeyError:
        return rule_name


def run(
    rules: list[Rule],
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    exchange_slug: str = "",
) -> list[RuleMatch]:
    """Evaluate all rules against a DataFrame and return matches.

    Args:
        rules: List of Rule instances to evaluate.
        df: DataFrame with OHLCV data and pre-computed indicator columns.
        symbol: Trading pair symbol the data belongs to.
        timeframe: Candle timeframe the data belongs to.
        exchange_slug: Exchange slug for the pair, e.g. "binance".

    Returns:
        List of RuleMatch for every rule whose conditions all returned True.
        Returns an empty list if no rules matched.
    """
    candle_timestamp: datetime = (
        pd.Timestamp(df["timestamp"].iloc[-1]).to_pydatetime()
        if "timestamp" in df.columns
        else datetime.now(timezone.utc)
    )
    if candle_timestamp.tzinfo is None:
        candle_timestamp = candle_timestamp.replace(tzinfo=timezone.utc)

    matches = []
    for rule in rules:
        if rule.evaluate(df):
            indicators = _extract_indicators(rule.name, df)
            matches.append(
                RuleMatch(
                    rule=rule,
                    symbol=symbol,
                    timeframe=timeframe,
                    message=_build_signal(rule.name, indicators),
                    exchange_slug=exchange_slug,
                    candle_timestamp=candle_timestamp,
                    indicators=indicators,
                )
            )
    return matches
