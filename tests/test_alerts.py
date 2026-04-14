"""Tests for candle.alerts.telegram."""

from datetime import datetime, timezone

import pytest
from telegram.error import TelegramError

from candle.alerts.telegram import format_message, send_alert, send_error_alert
from candle.screener.engine import RuleMatch
from candle.screener.rules import Rule


@pytest.fixture
def sample_match() -> RuleMatch:
    """A RuleMatch for use in alert formatting and delivery tests."""
    rule = Rule(name="EMA Crossover + RSI Oversold")
    return RuleMatch(
        rule=rule,
        symbol="BTC/USDT",
        timeframe="4h",
        message="EMA 9 crossed above EMA 21; RSI at 32",
        exchange_slug="binance",
        candle_timestamp=datetime(2026, 3, 30, 20, 0, 0, tzinfo=timezone.utc),
        indicators={"close": 83450.0, "ema_9": 83120.0, "ema_21": 82890.0},
    )


@pytest.fixture
def mock_bot(mocker):
    """A mock telegram.Bot that captures send_message calls."""
    bot = mocker.AsyncMock()
    mocker.patch("candle.alerts.telegram.Bot", return_value=bot)
    return bot


class TestFormatMessage:
    def test_includes_symbol(self, sample_match):
        """Formatted message must include the trading pair symbol."""
        assert "BTC/USDT" in format_message(sample_match)

    def test_includes_alert_message(self, sample_match):
        """Formatted message must include the alert description."""
        assert "EMA 9 crossed above EMA 21" in format_message(sample_match)

    def test_includes_timeframe(self, sample_match):
        """Formatted message must include the timeframe."""
        assert "4h" in format_message(sample_match)

    def test_returns_string(self, sample_match):
        assert isinstance(format_message(sample_match), str)


class TestSendAlert:
    async def test_calls_telegram_with_formatted_message(self, sample_match, mock_telegram, mocker):
        """send_alert must call the Telegram bot with the formatted message."""
        await send_alert(sample_match, bot=mock_telegram)

        mock_telegram.send_message.assert_called_once()
        call_kwargs = mock_telegram.send_message.call_args.kwargs
        assert "BTC/USDT" in call_kwargs["text"]
        assert "EMA 9 crossed above EMA 21" in call_kwargs["text"]

    async def test_send_alert_passes_chat_id(self, sample_match, mock_telegram, mocker):
        """send_alert must use the chat_id from settings."""
        mocker.patch("candle.alerts.telegram.settings.telegram_chat_id", "99999")
        await send_alert(sample_match, bot=mock_telegram)
        call_kwargs = mock_telegram.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == "99999"

    async def test_send_alert_uses_markdown_parse_mode(self, sample_match, mock_telegram):
        """send_alert must request Markdown formatting."""
        await send_alert(sample_match, bot=mock_telegram)
        call_kwargs = mock_telegram.send_message.call_args.kwargs
        assert call_kwargs["parse_mode"] == "Markdown"

    async def test_skips_send_when_token_not_configured(self, sample_match, mocker):
        """send_alert must not call the Telegram API when bot token is empty."""
        mocker.patch("candle.alerts.telegram.settings.telegram_bot_token", "")
        mock_bot_class = mocker.patch("candle.alerts.telegram.Bot")

        await send_alert(sample_match)  # no bot passed — should detect empty token

        mock_bot_class.assert_not_called()

    async def test_propagates_telegram_error(self, sample_match, mock_telegram):
        """TelegramError raised by the bot must propagate to the caller."""
        mock_telegram.send_message.side_effect = TelegramError("network failure")
        with pytest.raises(TelegramError, match="network failure"):
            await send_alert(sample_match, bot=mock_telegram)


class TestSendErrorAlert:
    async def test_message_contains_job_name_and_error(self, mocker):
        """Error alert must include the job name, error type, and error message."""
        mock_bot = mocker.AsyncMock()
        mocker.patch("candle.alerts.telegram.settings.telegram_bot_token", "tok")
        mocker.patch("candle.alerts.telegram.settings.telegram_admin_chat_id", "999")
        mocker.patch("candle.alerts.telegram.Bot", return_value=mock_bot)

        await send_error_alert("fetch_job", ValueError("db is down"))

        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == "999"
        text = call_kwargs["text"]
        assert "fetch_job" in text
        assert "ValueError" in text
        assert "db is down" in text

    async def test_skips_when_token_not_configured(self, mocker):
        """send_error_alert must not call the Telegram API when bot token is empty."""
        mocker.patch("candle.alerts.telegram.settings.telegram_bot_token", "")
        mock_bot_class = mocker.patch("candle.alerts.telegram.Bot")

        await send_error_alert("fetch_job", RuntimeError("oops"))

        mock_bot_class.assert_not_called()

    async def test_does_not_raise_on_telegram_error(self, mocker):
        """TelegramError during error alert must not propagate — scheduler must keep running."""
        mock_bot = mocker.AsyncMock()
        mock_bot.send_message.side_effect = TelegramError("offline")
        mocker.patch("candle.alerts.telegram.settings.telegram_bot_token", "tok")
        mocker.patch("candle.alerts.telegram.settings.telegram_admin_chat_id", "999")
        mocker.patch("candle.alerts.telegram.Bot", return_value=mock_bot)

        # Must not raise even though Telegram is offline.
        await send_error_alert("screen_job", RuntimeError("crash"))
