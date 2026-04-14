"""APScheduler job definitions.

Wires the data fetcher, indicator computation, screener engine, and alert sender
into scheduled jobs. Entry point for running the scheduler manually during development:

    python -m candle.scheduler.jobs --once
"""

import argparse
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from functools import partial

import ccxt.async_support as ccxt
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from candle.alerts.telegram import send_alert, send_error_alert
from candle.config import settings
from candle.data.exchange_factory import build_exchange
from candle.data.fetcher import fetch_ohlcv
from candle.db.models import ScreenerRule
from candle.db.repository import (
    get_active_pairs,
    get_active_rules,
    get_candles,
    get_recent_alert,
    mark_alert_sent,
    save_alert,
    save_candles,
)
from candle.db.session import AsyncSessionFactory
from candle.indicators.compute import compute_indicators
from candle.screener import engine as screener_engine
from candle.screener.conditions import (
    ema_crossover,
    ema_trending,
    price_above_vwap,
    rsi_range,
    volume_spike,
)
from candle.screener.rules import Rule

logger = logging.getLogger(__name__)

# Maps condition type strings (from the DB JSON) to their condition functions.
# Add a new entry here when introducing a new condition primitive.
_CONDITION_REGISTRY: dict[str, object] = {
    "ema_crossover": ema_crossover,
    "ema_trending": ema_trending,
    "rsi_range": rsi_range,
    "price_above_vwap": price_above_vwap,
    "volume_spike": volume_spike,
}


def _build_rule(db_rule: ScreenerRule) -> Rule:
    """Convert a ScreenerRule DB model to a callable Rule.

    Reads the conditions JSON list and binds each entry to the corresponding
    condition primitive via functools.partial.

    Supported condition types and required keys:
        - ``ema_crossover``: ``fast`` (int), ``slow`` (int)
        - ``rsi_range``:     ``min`` (float), ``max`` (float)
        - ``price_above_vwap``: no extra keys
        - ``volume_spike``:  ``multiplier`` (float)

    Args:
        db_rule: An active ScreenerRule with a populated conditions JSON list.

    Returns:
        A Rule instance with bound callable conditions.

    Raises:
        ValueError: If a condition type is not recognised.
        KeyError: If a required parameter is missing from the condition dict.
    """
    condition_fns = []
    for cond in db_rule.conditions:
        ctype = cond["type"]
        if ctype not in _CONDITION_REGISTRY:
            raise ValueError(f"unknown condition type: {ctype!r}")
        if ctype == "ema_crossover":
            condition_fns.append(partial(ema_crossover, fast=cond["fast"], slow=cond["slow"]))
        elif ctype == "ema_trending":
            condition_fns.append(partial(ema_trending, fast=cond["fast"], slow=cond["slow"]))
        elif ctype == "rsi_range":
            condition_fns.append(partial(rsi_range, min_val=cond["min"], max_val=cond["max"]))
        elif ctype == "price_above_vwap":
            condition_fns.append(price_above_vwap)
        elif ctype == "volume_spike":
            condition_fns.append(partial(volume_spike, multiplier=cond["multiplier"]))
    return Rule(name=db_rule.name, conditions=condition_fns)


async def fetch_job() -> None:
    """Fetch OHLCV data for all active pairs and persist to the database.

    Iterates over all active TradingPairs, fetches candles from the corresponding
    exchange, and calls repository.save_candles(). Handles exchange errors per pair
    without stopping the full run.

    On unhandled failure (e.g. DB unreachable), sends a Telegram error alert.
    """
    logger.info("fetch_job started", extra={"service": "fetch_job"})

    try:
        async with AsyncSessionFactory() as session:
            pairs = await get_active_pairs(session)

        logger.info(
            "fetch_job: pairs loaded",
            extra={"service": "fetch_job", "pair_count": len(pairs)},
        )

        pairs_processed = 0
        total_candles_saved = 0
        errors = 0

        for pair in pairs:
            exchange = build_exchange(pair.exchange.slug, settings)
            try:
                df = await fetch_ohlcv(exchange, pair.symbol, pair.timeframe)
                async with AsyncSessionFactory() as session:
                    async with session.begin():
                        saved = await save_candles(session, pair.id, df)
                pairs_processed += 1
                total_candles_saved += saved
                logger.info(
                    "fetch: pair processed",
                    extra={
                        "service": "fetch_job",
                        "exchange": pair.exchange.slug,
                        "symbol": pair.symbol,
                        "timeframe": pair.timeframe,
                        "candles_saved": saved,
                    },
                )
            except (ccxt.NetworkError, ccxt.ExchangeError, ccxt.RateLimitExceeded) as exc:
                errors += 1
                logger.error(
                    "fetch: exchange error",
                    extra={
                        "service": "fetch_job",
                        "exchange": pair.exchange.slug,
                        "symbol": pair.symbol,
                        "timeframe": pair.timeframe,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
            finally:
                await exchange.close()

        logger.info(
            "fetch_job completed",
            extra={
                "service": "fetch_job",
                "event": "heartbeat",
                "pairs_processed": pairs_processed,
                "total_candles_saved": total_candles_saved,
                "errors": errors,
            },
        )

    except Exception as exc:
        logger.error(
            "fetch_job failed",
            extra={
                "service": "fetch_job",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        await send_error_alert("fetch_job", exc)


async def screen_job() -> None:
    """Load candles, compute indicators, evaluate rules, and send alerts.

    For each active TradingPair:
    1. Load recent candles from the database.
    2. Compute all required indicators.
    3. Run all active ScreenerRules through the engine.
    4. Persist and deliver any RuleMatches via the alerts layer.

    Deduplication: an alert is skipped when the same rule already fired on the
    same pair within the last ``settings.alert_dedup_hours`` hours.

    On unhandled failure (e.g. DB unreachable), sends a Telegram error alert.
    """
    logger.info("screen_job started", extra={"service": "screen_job"})

    try:
        async with AsyncSessionFactory() as session:
            pairs = await get_active_pairs(session)
            db_rules = await get_active_rules(session)

        if not db_rules:
            logger.info(
                "screen_job: no active rules — skipping",
                extra={"service": "screen_job"},
            )
            return

        # Build callable Rules from DB models; skip malformed rules without crashing.
        rules: list[tuple[ScreenerRule, Rule]] = []
        for db_rule in db_rules:
            try:
                rules.append((db_rule, _build_rule(db_rule)))
            except (ValueError, KeyError) as exc:
                logger.error(
                    "screen_job: skipping malformed rule",
                    extra={
                        "service": "screen_job",
                        "rule": db_rule.name,
                        "error": str(exc),
                    },
                )

        if not rules:
            logger.warning(
                "screen_job: all rules failed to build — skipping",
                extra={"service": "screen_job"},
            )
            return

        callable_rules = [rule for _, rule in rules]

        pairs_screened = 0
        matches_found = 0
        alerts_sent = 0
        alerts_deduped = 0

        for pair in pairs:
            async with AsyncSessionFactory() as session:
                df = await get_candles(session, pair.id, limit=500)

            if df.empty:
                logger.warning(
                    "screen_job: no candles for pair — skipping",
                    extra={
                        "service": "screen_job",
                        "exchange": pair.exchange.slug,
                        "symbol": pair.symbol,
                        "timeframe": pair.timeframe,
                    },
                )
                continue

            compute_indicators(df)
            matches = screener_engine.run(
                callable_rules, df, pair.symbol, pair.timeframe,
                exchange_slug=pair.exchange.slug,
            )
            pairs_screened += 1
            matches_found += len(matches)

            if not matches:
                continue

            now = datetime.now(tz=timezone.utc)
            for match in matches:
                db_rule = next(dr for dr, r in rules if r.name == match.rule.name)
                dedup_window = timedelta(hours=db_rule.dedup_hours)

                async with AsyncSessionFactory() as session:
                    async with session.begin():
                        recent = await get_recent_alert(
                            session,
                            rule_id=db_rule.id,
                            pair_id=pair.id,
                            since=now - dedup_window,
                        )
                        if recent is not None:
                            alerts_deduped += 1
                            logger.debug(
                                "screen_job: alert deduped",
                                extra={
                                    "service": "screen_job",
                                    "symbol": pair.symbol,
                                    "rule": db_rule.name,
                                    "last_alert_at": str(recent.triggered_at),
                                },
                            )
                            continue

                        alert = await save_alert(
                            session,
                            rule_id=db_rule.id,
                            pair_id=pair.id,
                            user_id=db_rule.user_id,
                            triggered_at=now,
                            message=match.message,
                        )

                user_chat_id = db_rule.user.telegram_chat_id if db_rule.user else ""
                try:
                    await send_alert(
                        match,
                        chat_id=user_chat_id or settings.telegram_chat_id,
                    )
                    async with AsyncSessionFactory() as session:
                        async with session.begin():
                            await mark_alert_sent(session, alert.id)
                    alerts_sent += 1
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "screen_job: failed to deliver alert",
                        extra={
                            "service": "screen_job",
                            "exchange": pair.exchange.slug,
                            "symbol": pair.symbol,
                            "rule": db_rule.name,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )

        logger.info(
            "screen_job completed",
            extra={
                "service": "screen_job",
                "event": "heartbeat",
                "pairs_screened": pairs_screened,
                "rules_evaluated": pairs_screened * len(rules),
                "matches_found": matches_found,
                "alerts_sent": alerts_sent,
                "alerts_deduped": alerts_deduped,
            },
        )

    except Exception as exc:
        logger.error(
            "screen_job failed",
            extra={
                "service": "screen_job",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        await send_error_alert("screen_job", exc)


def build_scheduler() -> AsyncIOScheduler:
    """Build and return a configured AsyncIOScheduler.

    Returns:
        An APScheduler AsyncIOScheduler with fetch_job and screen_job registered
        according to FETCH_INTERVAL_MINUTES and SCREEN_INTERVAL_MINUTES from settings.
    """
    now = datetime.now(tz=timezone.utc)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        fetch_job,
        trigger=IntervalTrigger(minutes=settings.fetch_interval_minutes),
        id="fetch_job",
        name="Fetch OHLCV candles",
        misfire_grace_time=300,
        next_run_time=now,
    )
    scheduler.add_job(
        screen_job,
        trigger=IntervalTrigger(minutes=settings.screen_interval_minutes),
        id="screen_job",
        name="Screen rules and send alerts",
        misfire_grace_time=300,
        next_run_time=now,
    )
    return scheduler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Candle scheduler jobs")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run fetch and screen jobs once and exit (development mode)",
    )
    args = parser.parse_args()

    if args.once:
        async def _run_once() -> None:
            await fetch_job()
            await screen_job()

        asyncio.run(_run_once())
    else:
        scheduler = build_scheduler()
        scheduler.start()
