"""Seed script — inserts initial data for local development.

Idempotent: safe to run multiple times. Skips records that already exist.

Usage:
    python scripts/seed.py
"""

import asyncio

from sqlalchemy import select

from candle.db.models import Exchange, ScreenerRule, TradingPair
from candle.db.session import AsyncSessionFactory

EXCHANGES = [
    {"name": "Binance", "slug": "binance"},
    {"name": "Bit2Me", "slug": "bit2me"},
]

PAIRS = [
    # Binance
    ("binance", "BTC/USDT", "4h"),
    ("binance", "ETH/USDT", "4h"),
    ("binance", "SOL/USDT", "4h"),
    ("binance", "BNB/USDT", "4h"),
    ("binance", "BTC/USDT", "1d"),
    ("binance", "ETH/USDT", "1d"),
    # Bit2Me
    ("bit2me", "BTC/EUR", "4h"),
    ("bit2me", "ETH/EUR", "4h"),
]

RULES = [
    {
        "name": "EMA Crossover 9/21",
        "description": "Fast EMA (9) crosses above slow EMA (21) — bullish momentum signal.",
        "conditions": [{"type": "ema_crossover", "fast": 9, "slow": 21}],
        "dedup_hours": 4,
    },
    {
        "name": "EMA Trending 9/21",
        "description": "Fast EMA (9) is above slow EMA (21) — sustained bullish trend.",
        "conditions": [{"type": "ema_trending", "fast": 9, "slow": 21}],
        "dedup_hours": 24,
    },
    {
        "name": "RSI Oversold",
        "description": "RSI below 30 — potential reversal zone.",
        "conditions": [{"type": "rsi_range", "min": 0, "max": 30}],
        "dedup_hours": 24,
    },
    {
        "name": "RSI Overbought",
        "description": "RSI above 70 — bullish momentum, watch for exhaustion.",
        "conditions": [{"type": "rsi_range", "min": 70, "max": 100}],
        "dedup_hours": 24,
    },
    {
        "name": "Price Above VWAP",
        "description": "Close price above VWAP — institutional buying bias.",
        "conditions": [{"type": "price_above_vwap"}],
        "dedup_hours": 48,
    },
    {
        "name": "Volume Spike 2x",
        "description": "Volume exceeds 2x the 20-candle rolling average — unusual activity.",
        "conditions": [{"type": "volume_spike", "multiplier": 2.0}],
        "dedup_hours": 4,
    },
]


async def seed() -> None:
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # --- Exchanges ---
            exchanges: dict[str, Exchange] = {}
            for ex_def in EXCHANGES:
                result = await session.execute(
                    select(Exchange).where(Exchange.slug == ex_def["slug"])
                )
                exchange = result.scalar_one_or_none()
                if exchange is None:
                    exchange = Exchange(name=ex_def["name"], slug=ex_def["slug"])
                    session.add(exchange)
                    await session.flush()
                    print(f"  Created exchange: {exchange.name} (id={exchange.id})")
                else:
                    print(f"  Exchange already exists: {exchange.name} (id={exchange.id})")
                exchanges[ex_def["slug"]] = exchange

            # --- Trading pairs ---
            for slug, symbol, timeframe in PAIRS:
                exchange = exchanges[slug]
                result = await session.execute(
                    select(TradingPair).where(
                        TradingPair.exchange_id == exchange.id,
                        TradingPair.symbol == symbol,
                        TradingPair.timeframe == timeframe,
                    )
                )
                pair = result.scalar_one_or_none()
                if pair is None:
                    pair = TradingPair(
                        exchange_id=exchange.id,
                        symbol=symbol,
                        timeframe=timeframe,
                        active=True,
                    )
                    session.add(pair)
                    await session.flush()
                    print(f"  Created pair: {pair.symbol} {pair.timeframe} @ {slug} (id={pair.id})")
                else:
                    print(f"  Pair already exists: {pair.symbol} {pair.timeframe} @ {slug} (id={pair.id})")

            # --- Screener rules (owned by seed admin user id=1) ---
            for rule_def in RULES:
                result = await session.execute(
                    select(ScreenerRule).where(ScreenerRule.name == rule_def["name"])
                )
                rule = result.scalar_one_or_none()
                if rule is None:
                    rule = ScreenerRule(
                        user_id=1,
                        name=rule_def["name"],
                        description=rule_def["description"],
                        conditions=rule_def["conditions"],
                        dedup_hours=rule_def.get("dedup_hours", 4),
                        active=True,
                    )
                    session.add(rule)
                    await session.flush()
                    print(f"  Created rule: {rule.name} (id={rule.id})")
                else:
                    print(f"  Rule already exists: {rule.name} (id={rule.id})")

    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
