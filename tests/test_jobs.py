"""Tests for candle.scheduler.jobs — _build_rule, _compute_indicators, fetch_job, screen_job."""

from unittest.mock import AsyncMock, MagicMock

import ccxt.async_support as ccxt
import numpy as np
import pandas as pd
import pytest

from candle.db.models import Exchange, ScreenerRule, TradingPair
from candle.indicators.compute import compute_indicators
from candle.scheduler.jobs import _build_rule
from candle.screener.rules import Rule


# ---------------------------------------------------------------------------
# Job-level failure tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pair(
    pair_id: int = 1,
    symbol: str = "BTC/USDT",
    timeframe: str = "4h",
    exchange_slug: str = "binance",
) -> MagicMock:
    exchange = MagicMock(spec=Exchange)
    exchange.slug = exchange_slug
    pair = MagicMock(spec=TradingPair)
    pair.id = pair_id
    pair.symbol = symbol
    pair.timeframe = timeframe
    pair.exchange = exchange
    return pair


def _make_db_rule(
    rule_id: int = 1,
    name: str = "Test Rule",
    conditions: list | None = None,
    user_telegram_chat_id: str = "99999",
) -> MagicMock:
    user = MagicMock()
    user.telegram_chat_id = user_telegram_chat_id
    db_rule = MagicMock(spec=ScreenerRule)
    db_rule.id = rule_id
    db_rule.user_id = 1
    db_rule.name = name
    db_rule.conditions = conditions or [{"type": "price_above_vwap"}]
    db_rule.dedup_hours = 4
    db_rule.user = user
    return db_rule


def _make_candle_df(n: int = 250) -> pd.DataFrame:
    """Return a realistic OHLCV DataFrame with enough rows for all indicators."""
    np.random.seed(42)
    close = np.cumsum(np.random.randn(n)) + 100
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="4h"),
        "open": close - 0.5,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": np.ones(n) * 500.0,
    })


@pytest.fixture
def mock_session_factory(mocker):
    """Patch AsyncSessionFactory so jobs run without a real database.

    Returns a mock session whose begin() context manager is also mocked.
    """
    session = mocker.AsyncMock()

    begin_ctx = MagicMock()
    begin_ctx.__aenter__ = AsyncMock(return_value=None)
    begin_ctx.__aexit__ = AsyncMock(return_value=False)
    # session.begin must be a plain MagicMock so that session.begin() returns
    # begin_ctx directly (not wrapped in a coroutine). AsyncMock would make it
    # return a coroutine, which is not an async context manager.
    session.begin = MagicMock(return_value=begin_ctx)

    factory_ctx = MagicMock()
    factory_ctx.__aenter__ = AsyncMock(return_value=session)
    factory_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_factory = mocker.patch("candle.scheduler.jobs.AsyncSessionFactory")
    mock_factory.return_value = factory_ctx
    return session


# ---------------------------------------------------------------------------
# _build_rule
# ---------------------------------------------------------------------------

class TestBuildRule:
    def test_ema_crossover_creates_rule(self):
        db_rule = _make_db_rule(conditions=[{"type": "ema_crossover", "fast": 9, "slow": 21}])
        rule = _build_rule(db_rule)
        assert isinstance(rule, Rule)
        assert len(rule.conditions) == 1

    def test_rsi_range_creates_rule(self):
        db_rule = _make_db_rule(conditions=[{"type": "rsi_range", "min": 30.0, "max": 70.0}])
        rule = _build_rule(db_rule)
        assert len(rule.conditions) == 1

    def test_price_above_vwap_creates_rule(self):
        db_rule = _make_db_rule(conditions=[{"type": "price_above_vwap"}])
        rule = _build_rule(db_rule)
        assert len(rule.conditions) == 1

    def test_volume_spike_creates_rule(self):
        db_rule = _make_db_rule(conditions=[{"type": "volume_spike", "multiplier": 2.0}])
        rule = _build_rule(db_rule)
        assert len(rule.conditions) == 1

    def test_multiple_conditions(self):
        db_rule = _make_db_rule(conditions=[
            {"type": "rsi_range", "min": 30.0, "max": 70.0},
            {"type": "price_above_vwap"},
        ])
        rule = _build_rule(db_rule)
        assert len(rule.conditions) == 2

    def test_rule_name_matches_db_rule(self):
        db_rule = _make_db_rule(name="My Signal", conditions=[{"type": "price_above_vwap"}])
        rule = _build_rule(db_rule)
        assert rule.name == "My Signal"

    def test_unknown_type_raises_value_error(self):
        db_rule = _make_db_rule(conditions=[{"type": "nonexistent_condition"}])
        with pytest.raises(ValueError, match="unknown condition type"):
            _build_rule(db_rule)

    def test_missing_param_raises_key_error(self):
        """ema_crossover without 'fast' key must raise KeyError."""
        db_rule = _make_db_rule(conditions=[{"type": "ema_crossover", "slow": 21}])
        with pytest.raises(KeyError):
            _build_rule(db_rule)

    def test_built_ema_crossover_evaluates_correctly(self):
        """The bound ema_crossover condition fires on a DataFrame with a real crossover."""
        db_rule = _make_db_rule(conditions=[{"type": "ema_crossover", "fast": 9, "slow": 21}])
        rule = _build_rule(db_rule)
        # Crossover: prev fast < prev slow, last fast >= last slow
        df = pd.DataFrame({"ema_9": [90.0, 100.0], "ema_21": [95.0, 99.0]})
        assert rule.evaluate(df) is True

    def test_built_rsi_range_evaluates_correctly(self):
        db_rule = _make_db_rule(conditions=[{"type": "rsi_range", "min": 30.0, "max": 70.0}])
        rule = _build_rule(db_rule)
        df = pd.DataFrame({"rsi": [50.0]})
        assert rule.evaluate(df) is True


# ---------------------------------------------------------------------------
# _compute_indicators
# ---------------------------------------------------------------------------

class TestComputeIndicators:
    def test_adds_all_expected_columns(self):
        df = _make_candle_df()
        result = compute_indicators(df)
        for col in ("ema_9", "ema_21", "ema_50", "ema_200", "rsi", "vwap"):
            assert col in result.columns, f"expected column '{col}' missing"

    def test_original_ohlcv_columns_preserved(self):
        df = _make_candle_df()
        result = compute_indicators(df)
        for col in ("open", "high", "low", "close", "volume"):
            assert col in result.columns

    def test_returns_same_dataframe(self):
        df = _make_candle_df()
        result = compute_indicators(df)
        assert result is df


# ---------------------------------------------------------------------------
# screen_job
# ---------------------------------------------------------------------------

class TestScreenJob:
    async def test_returns_early_when_no_active_rules(self, mocker, mock_session_factory):
        mocker.patch("candle.scheduler.jobs.get_active_pairs", return_value=[_make_pair()])
        mocker.patch("candle.scheduler.jobs.get_active_rules", return_value=[])
        mock_get_candles = mocker.patch("candle.scheduler.jobs.get_candles")

        from candle.scheduler.jobs import screen_job
        await screen_job()

        mock_get_candles.assert_not_called()

    async def test_skips_pair_with_empty_candles(self, mocker, mock_session_factory):
        db_rule = _make_db_rule()
        mocker.patch("candle.scheduler.jobs.get_active_pairs", return_value=[_make_pair()])
        mocker.patch("candle.scheduler.jobs.get_active_rules", return_value=[db_rule])
        mocker.patch(
            "candle.scheduler.jobs.get_candles",
            return_value=pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"]),
        )
        mock_save = mocker.patch("candle.scheduler.jobs.save_alert")

        from candle.scheduler.jobs import screen_job
        await screen_job()

        mock_save.assert_not_called()

    async def test_saves_and_sends_alert_on_match(self, mocker, mock_session_factory):
        pair = _make_pair()
        db_rule = _make_db_rule()
        df = _make_candle_df()

        mocker.patch("candle.scheduler.jobs.get_active_pairs", return_value=[pair])
        mocker.patch("candle.scheduler.jobs.get_active_rules", return_value=[db_rule])
        mocker.patch("candle.scheduler.jobs.get_candles", return_value=df)
        mocker.patch("candle.scheduler.jobs.get_recent_alert", return_value=None)

        saved_alert = MagicMock()
        saved_alert.id = 99
        mocker.patch("candle.scheduler.jobs.save_alert", return_value=saved_alert)
        mock_mark = mocker.patch("candle.scheduler.jobs.mark_alert_sent")
        mock_send = mocker.patch("candle.scheduler.jobs.send_alert", new_callable=AsyncMock)

        # Force the rule to always match regardless of indicator values.
        always_match = Rule(name=db_rule.name, conditions=[lambda df: True])
        mocker.patch("candle.scheduler.jobs._build_rule", return_value=always_match)

        from candle.scheduler.jobs import screen_job
        await screen_job()

        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs.get("chat_id") == "99999"
        mock_mark.assert_called_once_with(mocker.ANY, saved_alert.id)

    async def test_deduplication_skips_alert(self, mocker, mock_session_factory):
        """When get_recent_alert returns an alert, no new alert must be saved or sent."""
        pair = _make_pair()
        db_rule = _make_db_rule()
        df = _make_candle_df()

        mocker.patch("candle.scheduler.jobs.get_active_pairs", return_value=[pair])
        mocker.patch("candle.scheduler.jobs.get_active_rules", return_value=[db_rule])
        mocker.patch("candle.scheduler.jobs.get_candles", return_value=df)
        mocker.patch("candle.scheduler.jobs.get_recent_alert", return_value=MagicMock())

        mock_save = mocker.patch("candle.scheduler.jobs.save_alert")
        mock_send = mocker.patch("candle.scheduler.jobs.send_alert", new_callable=AsyncMock)

        always_match = Rule(name=db_rule.name, conditions=[lambda df: True])
        mocker.patch("candle.scheduler.jobs._build_rule", return_value=always_match)

        from candle.scheduler.jobs import screen_job
        await screen_job()

        mock_save.assert_not_called()
        mock_send.assert_not_called()

    async def test_telegram_error_does_not_crash_job(self, mocker, mock_session_factory):
        """A TelegramError during delivery must be caught; the job must complete normally."""
        from telegram.error import TelegramError

        pair = _make_pair()
        db_rule = _make_db_rule()
        df = _make_candle_df()

        mocker.patch("candle.scheduler.jobs.get_active_pairs", return_value=[pair])
        mocker.patch("candle.scheduler.jobs.get_active_rules", return_value=[db_rule])
        mocker.patch("candle.scheduler.jobs.get_candles", return_value=df)
        mocker.patch("candle.scheduler.jobs.get_recent_alert", return_value=None)

        saved_alert = MagicMock()
        saved_alert.id = 99
        mocker.patch("candle.scheduler.jobs.save_alert", return_value=saved_alert)
        mocker.patch("candle.scheduler.jobs.mark_alert_sent")

        mock_send = mocker.patch(
            "candle.scheduler.jobs.send_alert",
            new_callable=AsyncMock,
            side_effect=TelegramError("bot offline"),
        )

        always_match = Rule(name=db_rule.name, conditions=[lambda df: True])
        mocker.patch("candle.scheduler.jobs._build_rule", return_value=always_match)

        from candle.scheduler.jobs import screen_job
        await screen_job()  # must not raise

        mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# fetch_job
# ---------------------------------------------------------------------------

class TestFetchJob:
    async def test_fetches_and_saves_candles(self, mocker, mock_session_factory):
        pair = _make_pair()
        mocker.patch("candle.scheduler.jobs.get_active_pairs", return_value=[pair])

        df = _make_candle_df(100)
        mock_fetch = mocker.patch("candle.scheduler.jobs.fetch_ohlcv", return_value=df)
        mock_save = mocker.patch("candle.scheduler.jobs.save_candles", return_value=100)

        mock_exchange = mocker.AsyncMock()
        mocker.patch("candle.scheduler.jobs.build_exchange", return_value=mock_exchange)

        from candle.scheduler.jobs import fetch_job
        await fetch_job()

        mock_fetch.assert_called_once_with(mock_exchange, pair.symbol, pair.timeframe)
        mock_save.assert_called_once()
        mock_exchange.close.assert_called_once()

    async def test_exchange_close_called_even_on_error(self, mocker, mock_session_factory):
        """exchange.close() must be called in the finally block even when fetch fails."""
        pair = _make_pair()
        mocker.patch("candle.scheduler.jobs.get_active_pairs", return_value=[pair])
        mocker.patch(
            "candle.scheduler.jobs.fetch_ohlcv",
            side_effect=ccxt.NetworkError("timeout"),
        )
        mock_exchange = mocker.AsyncMock()
        mocker.patch("candle.scheduler.jobs.build_exchange", return_value=mock_exchange)
        mocker.patch("candle.scheduler.jobs.save_candles")

        from candle.scheduler.jobs import fetch_job
        await fetch_job()  # must not raise

        mock_exchange.close.assert_called_once()

    async def test_exchange_error_does_not_stop_loop(self, mocker, mock_session_factory):
        """A NetworkError on pair 1 must not prevent pair 2 from being fetched."""
        pair1 = _make_pair(pair_id=1, symbol="BTC/USDT")
        pair2 = _make_pair(pair_id=2, symbol="ETH/USDT")
        mocker.patch("candle.scheduler.jobs.get_active_pairs", return_value=[pair1, pair2])

        df = _make_candle_df(100)
        mock_fetch = mocker.patch(
            "candle.scheduler.jobs.fetch_ohlcv",
            side_effect=[ccxt.NetworkError("timeout"), df],
        )
        mock_save = mocker.patch("candle.scheduler.jobs.save_candles", return_value=100)
        mock_exchange = mocker.AsyncMock()
        mocker.patch("candle.scheduler.jobs.build_exchange", return_value=mock_exchange)

        from candle.scheduler.jobs import fetch_job
        await fetch_job()

        assert mock_fetch.call_count == 2
        mock_save.assert_called_once()  # only ETH/USDT succeeded


class TestJobFailureAlerts:
    async def test_fetch_job_sends_error_alert_on_db_failure(self, mocker, mock_session_factory):
        """fetch_job must call send_error_alert when get_active_pairs raises."""
        mocker.patch(
            "candle.scheduler.jobs.get_active_pairs",
            side_effect=RuntimeError("db connection refused"),
        )
        mock_error_alert = mocker.patch(
            "candle.scheduler.jobs.send_error_alert", new_callable=AsyncMock
        )

        from candle.scheduler.jobs import fetch_job
        await fetch_job()  # must not raise

        mock_error_alert.assert_called_once()
        job_name, error = mock_error_alert.call_args.args
        assert job_name == "fetch_job"
        assert isinstance(error, RuntimeError)

    async def test_screen_job_sends_error_alert_on_db_failure(self, mocker, mock_session_factory):
        """screen_job must call send_error_alert when get_active_pairs raises."""
        mocker.patch(
            "candle.scheduler.jobs.get_active_pairs",
            side_effect=RuntimeError("db connection refused"),
        )
        mock_error_alert = mocker.patch(
            "candle.scheduler.jobs.send_error_alert", new_callable=AsyncMock
        )

        from candle.scheduler.jobs import screen_job
        await screen_job()  # must not raise

        mock_error_alert.assert_called_once()
        job_name, error = mock_error_alert.call_args.args
        assert job_name == "screen_job"
        assert isinstance(error, RuntimeError)

    async def test_fetch_job_does_not_send_error_alert_for_exchange_error(
        self, mocker, mock_session_factory
    ):
        """Per-pair ccxt errors must NOT trigger send_error_alert — only complete failures do."""
        pair = _make_pair()
        mocker.patch("candle.scheduler.jobs.get_active_pairs", return_value=[pair])
        mocker.patch(
            "candle.scheduler.jobs.fetch_ohlcv",
            side_effect=ccxt.NetworkError("timeout"),
        )
        mock_exchange = mocker.AsyncMock()
        mocker.patch("candle.scheduler.jobs.build_exchange", return_value=mock_exchange)
        mock_error_alert = mocker.patch(
            "candle.scheduler.jobs.send_error_alert", new_callable=AsyncMock
        )

        from candle.scheduler.jobs import fetch_job
        await fetch_job()

        mock_error_alert.assert_not_called()
