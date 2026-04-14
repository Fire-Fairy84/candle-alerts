"""Telegram alert sender.

Formats RuleMatch objects into human-readable messages and delivers them
via the Telegram Bot API. Never called directly from the screener.
"""

import logging
from datetime import datetime, timezone

from telegram import Bot
from telegram.error import TelegramError

from candle.config import settings
from candle.screener.engine import RuleMatch

logger = logging.getLogger(__name__)


_RULE_EMOJI: dict[str, str] = {
    "EMA Crossover 9/21": "\U0001f504",   # arrows cycle — trend shift
    "RSI Oversold": "\U0001f4c9",          # chart decreasing — weakness
    "RSI Overbought": "\U0001f4c8",        # chart increasing — strength
    "Price Above VWAP": "\U00002705",      # check mark — bullish
    "Volume Spike 2x": "\U0001f4a5",       # boom — unusual activity
}


def _fmt_price(price: float) -> str:
    """Format a price with appropriate decimal places based on magnitude."""
    if price >= 1_000:
        return f"${price:,.0f}"
    if price >= 1:
        return f"${price:,.2f}"
    return f"${price:.4f}"


def _indicator_line(match: RuleMatch) -> str:
    """Build the rule-specific indicator line — only values that triggered the rule."""
    ind = match.indicators
    rule = match.rule.name
    if rule == "EMA Crossover 9/21":
        return f"EMA9: {_fmt_price(ind['ema_9'])} | EMA21: {_fmt_price(ind['ema_21'])}"
    if rule in ("RSI Oversold", "RSI Overbought"):
        return f"RSI: {ind['rsi']:.1f}"
    if rule == "Price Above VWAP":
        return f"VWAP: {_fmt_price(ind['vwap'])}"
    if rule == "Volume Spike 2x":
        return f"Vol: {ind['volume']:,.0f} (avg: {ind['avg_volume']:,.0f})"
    return ""


def _candle_time(candle_timestamp: datetime) -> str:
    """Format the candle's UTC timestamp as a short time string, e.g. '14:00 UTC'."""
    ts = candle_timestamp if candle_timestamp.tzinfo else candle_timestamp.replace(tzinfo=timezone.utc)
    return ts.strftime("%H:%M UTC")


def format_message(match: RuleMatch) -> str:
    """Format a RuleMatch into a structured Telegram message.

    Output (5 lines):
        {emoji} SYMBOL · timeframe · exchange
        Signal line (with direction bias)
        Price: $XX,XXX
        Rule-specific indicator values
        HH:MM UTC  (candle timestamp, always present)

    Args:
        match: The RuleMatch to format.

    Returns:
        A Markdown-formatted string ready to send via Telegram.
    """
    emoji = _RULE_EMOJI.get(match.rule.name, "\U0001f514")
    exchange = match.exchange_slug.capitalize() if match.exchange_slug else ""

    header = f"{emoji} *{match.symbol}* \u00b7 `{match.timeframe}`"
    if exchange:
        header += f" \u00b7 {exchange}"

    lines = [
        header,
        match.message,
        f"Price: {_fmt_price(match.indicators.get('close', 0.0))}",
        _indicator_line(match),
        _candle_time(match.candle_timestamp),
    ]
    return "\n".join(line for line in lines if line)


async def send_error_alert(job_name: str, error: Exception) -> None:
    """Send a scheduler failure notification to Telegram.

    Called when fetch_job or screen_job raises an unhandled exception that
    aborts the entire cycle. Per-pair exchange errors are NOT failures in
    this sense and must not trigger this function.

    Silently skips if TELEGRAM_BOT_TOKEN is not configured. Catches and logs
    TelegramError without re-raising — the scheduler must keep running.

    Args:
        job_name: Name of the failed job, e.g. "fetch_job".
        error: The exception that caused the failure.
    """
    if not settings.telegram_bot_token:
        logger.warning(
            "TELEGRAM_BOT_TOKEN not configured — skipping error alert",
            extra={"service": job_name},
        )
        return

    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = (
        f"\U0001f6a8 *Scheduler failure*\n"
        f"Job: `{job_name}`\n"
        f"Error: {type(error).__name__} — {error}\n"
        f"Time: {now}"
    )

    admin_chat_id = settings.telegram_admin_chat_id or settings.telegram_chat_id
    bot = Bot(token=settings.telegram_bot_token)
    try:
        await bot.send_message(
            chat_id=admin_chat_id,
            text=text,
            parse_mode="Markdown",
        )
        logger.info(
            "error alert sent",
            extra={"service": job_name, "error_type": type(error).__name__},
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "failed to send error alert",
            extra={"service": job_name, "error": str(exc)},
        )


async def send_alert(
    match: RuleMatch,
    bot: Bot | None = None,
    chat_id: str | None = None,
) -> None:
    """Format a RuleMatch and send it as a Telegram message.

    Uses TELEGRAM_BOT_TOKEN from settings. Silently skips if the token is empty
    (development mode).

    If bot is provided it is used directly; otherwise a Bot instance is created
    from settings. Pass a bot explicitly to reuse a single connection across
    multiple calls in the same job run, or to inject a mock in tests.

    The destination chat is resolved in order:
        1. ``chat_id`` argument (the rule owner's chat)
        2. ``settings.telegram_chat_id`` (global fallback for single-user mode)

    Args:
        match: The RuleMatch to format and deliver.
        bot: Optional pre-configured Bot instance.
        chat_id: Telegram chat ID to deliver the alert to. Overrides settings.

    Raises:
        telegram.error.TelegramError: On API-level delivery failures.
    """
    if bot is None:
        if not settings.telegram_bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured — skipping alert delivery")
            return
        bot = Bot(token=settings.telegram_bot_token)

    destination = chat_id or settings.telegram_chat_id
    text = format_message(match)
    await bot.send_message(
        chat_id=destination,
        text=text,
        parse_mode="Markdown",
    )
    logger.info("alert sent: %s / %s [%s]", match.symbol, match.rule.name, match.timeframe)
