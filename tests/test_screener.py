"""Tests for candle.screener — conditions, rules, and engine."""

from functools import partial

import pandas as pd
import pytest

from candle.indicators.momentum import rsi
from candle.indicators.trend import ema
from candle.indicators.volume import vwap
from candle.screener.conditions import (
    ema_crossover,
    price_above_vwap,
    rsi_range,
    volume_spike,
)
from candle.screener.engine import RuleMatch, run
from candle.screener.rules import Rule


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def crossover_df() -> pd.DataFrame:
    """Crossover fixture with ema_9 and ema_21 pre-computed (as the scheduler would)."""
    df = pd.read_csv("tests/fixtures/btc_4h_crossover.csv", parse_dates=["timestamp"])
    df["ema_9"] = ema(df, 9)
    df["ema_21"] = ema(df, 21)
    return df


@pytest.fixture
def overbought_df() -> pd.DataFrame:
    """Overbought fixture with rsi pre-computed."""
    df = pd.read_csv("tests/fixtures/btc_4h_overbought.csv", parse_dates=["timestamp"])
    df["rsi"] = rsi(df)
    return df


@pytest.fixture
def btc_4h() -> pd.DataFrame:
    """100-candle fixture with vwap pre-computed."""
    df = pd.read_csv("tests/fixtures/btc_4h_100.csv", parse_dates=["timestamp"])
    df["vwap"] = vwap(df)
    return df


def _make_df(**kwargs) -> pd.DataFrame:
    """Build a minimal DataFrame from keyword-argument columns."""
    return pd.DataFrame(kwargs)


# ---------------------------------------------------------------------------
# ema_crossover
# ---------------------------------------------------------------------------

class TestEmaCrossover:
    def test_detects_crossover_in_fixture(self, crossover_df):
        """Real fixture: EMA(9) crossed above EMA(21) on the last candle."""
        assert ema_crossover(crossover_df, fast=9, slow=21) is True

    def test_no_crossover_when_fast_always_above(self):
        """No crossover when fast EMA has been above slow EMA for multiple candles."""
        df = _make_df(ema_9=[100.0, 110.0, 120.0], ema_21=[90.0, 95.0, 100.0])
        assert ema_crossover(df, fast=9, slow=21) is False

    def test_no_crossover_when_fast_always_below(self):
        """No crossover when fast EMA stays below slow EMA."""
        df = _make_df(ema_9=[80.0, 85.0, 88.0], ema_21=[90.0, 95.0, 100.0])
        assert ema_crossover(df, fast=9, slow=21) is False

    def test_raises_value_error_with_single_row(self):
        """ValueError when DataFrame has fewer than 2 rows."""
        df = _make_df(ema_9=[100.0], ema_21=[90.0])
        with pytest.raises(ValueError, match="at least 2 rows"):
            ema_crossover(df, fast=9, slow=21)

    def test_raises_key_error_on_missing_fast_column(self):
        """KeyError when the fast EMA column is absent."""
        df = _make_df(ema_21=[90.0, 95.0])
        with pytest.raises(KeyError, match="ema_9"):
            ema_crossover(df, fast=9, slow=21)

    def test_raises_key_error_on_missing_slow_column(self):
        """KeyError when the slow EMA column is absent."""
        df = _make_df(ema_9=[90.0, 95.0])
        with pytest.raises(KeyError, match="ema_21"):
            ema_crossover(df, fast=9, slow=21)


# ---------------------------------------------------------------------------
# rsi_range
# ---------------------------------------------------------------------------

class TestRsiRange:
    def test_returns_true_when_in_range(self, overbought_df):
        """Real fixture: RSI(14) > 70 → in range [65, 80]."""
        assert rsi_range(overbought_df, min_val=65.0, max_val=80.0) is True

    def test_returns_false_when_above_range(self, overbought_df):
        """RSI of ~70.7 is not in range [0, 50]."""
        assert rsi_range(overbought_df, min_val=0.0, max_val=50.0) is False

    def test_returns_false_when_below_range(self):
        df = _make_df(rsi=[25.0])
        assert rsi_range(df, min_val=30.0, max_val=70.0) is False

    def test_boundary_inclusive_lower(self):
        df = _make_df(rsi=[30.0])
        assert rsi_range(df, min_val=30.0, max_val=70.0) is True

    def test_boundary_inclusive_upper(self):
        df = _make_df(rsi=[70.0])
        assert rsi_range(df, min_val=30.0, max_val=70.0) is True

    def test_raises_key_error_on_missing_column(self):
        df = _make_df(close=[100.0])
        with pytest.raises(KeyError, match="rsi"):
            rsi_range(df, min_val=30.0, max_val=70.0)

    def test_weak_bearish_zone_fires(self):
        """RSI ~40 (typical bearish market) triggers the widened 0-45 range."""
        df = _make_df(rsi=[39.55])
        assert rsi_range(df, min_val=0.0, max_val=45.0) is True

    def test_boundary_inclusive_upper_45(self):
        """RSI exactly 45 → inclusive upper bound, triggers."""
        df = _make_df(rsi=[45.0])
        assert rsi_range(df, min_val=0.0, max_val=45.0) is True

    def test_boundary_exclusive_above_45(self):
        """RSI 46 → above the widened range, does not trigger."""
        df = _make_df(rsi=[46.0])
        assert rsi_range(df, min_val=0.0, max_val=45.0) is False


# ---------------------------------------------------------------------------
# price_above_vwap
# ---------------------------------------------------------------------------

class TestPriceAboveVwap:
    def test_returns_true_when_close_above_vwap(self, btc_4h):
        """Real fixture: last candle close (71618) > vwap (70802)."""
        assert price_above_vwap(btc_4h) is True

    def test_returns_false_when_close_below_vwap(self):
        df = _make_df(close=[99.0], vwap=[100.0])
        assert price_above_vwap(df) is False

    def test_returns_false_when_close_equals_vwap(self):
        """Not strictly above → False."""
        df = _make_df(close=[100.0], vwap=[100.0])
        assert price_above_vwap(df) is False

    def test_raises_key_error_on_missing_vwap(self):
        df = _make_df(close=[100.0])
        with pytest.raises(KeyError, match="vwap"):
            price_above_vwap(df)

    def test_raises_key_error_on_missing_close(self):
        df = _make_df(vwap=[100.0])
        with pytest.raises(KeyError, match="close"):
            price_above_vwap(df)


# ---------------------------------------------------------------------------
# volume_spike
# ---------------------------------------------------------------------------

class TestVolumeSpike:
    def _spike_df(self, window: int = 20, multiplier_factor: float = 3.0) -> pd.DataFrame:
        """Build a DataFrame where the last candle's volume is multiplier_factor × the mean."""
        baseline = [1000.0] * (window + 1)
        baseline[-1] = 1000.0 * multiplier_factor
        return _make_df(volume=baseline)

    def test_detects_spike_above_multiplier(self):
        """Last candle at 3× the baseline → spike with multiplier=2."""
        df = self._spike_df(multiplier_factor=3.0)
        assert volume_spike(df, multiplier=2.0) is True

    def test_no_spike_on_normal_volume(self):
        """Uniform volume → no spike at multiplier=2."""
        df = _make_df(volume=[1000.0] * 21)
        assert volume_spike(df, multiplier=2.0) is False

    def test_no_spike_just_below_threshold(self):
        """Last candle at 1.9× baseline does not trigger multiplier=2."""
        baseline = [1000.0] * 21
        baseline[-1] = 1900.0
        df = _make_df(volume=baseline)
        assert volume_spike(df, multiplier=2.0) is False

    def test_exact_threshold_triggers(self):
        """Last candle exactly at threshold (>=) should trigger."""
        baseline = [1000.0] * 21
        baseline[-1] = 2000.0
        df = _make_df(volume=baseline)
        assert volume_spike(df, multiplier=2.0) is True

    def test_raises_value_error_on_insufficient_rows(self):
        """ValueError when df has fewer than window + 1 rows."""
        df = _make_df(volume=[1000.0] * 5)
        with pytest.raises(ValueError, match="window=20"):
            volume_spike(df, multiplier=2.0, window=20)

    def test_raises_key_error_on_missing_column(self):
        df = _make_df(close=[100.0] * 21)
        with pytest.raises(KeyError, match="volume"):
            volume_spike(df, multiplier=2.0)

    def test_lower_multiplier_1_5_detects_moderate_spike(self):
        """Volume at 1.6× baseline triggers multiplier=1.5."""
        baseline = [1000.0] * 21
        baseline[-1] = 1600.0
        df = _make_df(volume=baseline)
        assert volume_spike(df, multiplier=1.5) is True

    def test_lower_multiplier_1_5_exact_boundary(self):
        """Volume exactly 1.5× baseline (>= threshold) triggers."""
        baseline = [1000.0] * 21
        baseline[-1] = 1500.0
        df = _make_df(volume=baseline)
        assert volume_spike(df, multiplier=1.5) is True

    def test_lower_multiplier_1_5_just_below(self):
        """Volume at 1.49× baseline does not trigger multiplier=1.5."""
        baseline = [1000.0] * 21
        baseline[-1] = 1490.0
        df = _make_df(volume=baseline)
        assert volume_spike(df, multiplier=1.5) is False


# ---------------------------------------------------------------------------
# Rule — composed conditions
# ---------------------------------------------------------------------------

class TestRuleComposed:
    """Tests for Rule with real condition functions (production-like configurations)."""

    def test_rsi_weak_and_volume_spike_both_met(self):
        """Rule with RSI(0-45) AND volume_spike(1.5) fires when both conditions hold."""
        volumes = [1000.0] * 21
        volumes[-1] = 1600.0
        df = _make_df(rsi=[40.0] * 21, volume=volumes)
        rule = Rule(
            name="Bearish + Volume",
            conditions=[
                partial(rsi_range, min_val=0.0, max_val=45.0),
                partial(volume_spike, multiplier=1.5),
            ],
        )
        assert rule.evaluate(df) is True

    def test_rsi_weak_met_but_no_volume_spike(self):
        """Rule requires both — RSI in range but normal volume → False."""
        df = _make_df(rsi=[40.0] * 21, volume=[1000.0] * 21)
        rule = Rule(
            name="Bearish + Volume",
            conditions=[
                partial(rsi_range, min_val=0.0, max_val=45.0),
                partial(volume_spike, multiplier=1.5),
            ],
        )
        assert rule.evaluate(df) is False

    def test_volume_spike_met_but_rsi_out_of_range(self):
        """Rule requires both — volume spikes but RSI too high → False."""
        volumes = [1000.0] * 21
        volumes[-1] = 1600.0
        df = _make_df(rsi=[55.0] * 21, volume=volumes)
        rule = Rule(
            name="Bearish + Volume",
            conditions=[
                partial(rsi_range, min_val=0.0, max_val=45.0),
                partial(volume_spike, multiplier=1.5),
            ],
        )
        assert rule.evaluate(df) is False


class TestRule:
    def test_returns_true_when_all_conditions_pass(self):
        rule = Rule(name="all pass", conditions=[lambda df: True, lambda df: True])
        assert rule.evaluate(_make_df(close=[1.0])) is True

    def test_returns_false_when_any_condition_fails(self):
        rule = Rule(name="one fails", conditions=[lambda df: True, lambda df: False])
        assert rule.evaluate(_make_df(close=[1.0])) is False

    def test_returns_true_vacuously_with_no_conditions(self):
        rule = Rule(name="empty")
        assert rule.evaluate(_make_df(close=[1.0])) is True

    def test_short_circuits_on_first_false(self):
        """Second condition must not be called if first returns False."""
        calls = []

        def first(df):
            calls.append("first")
            return False

        def second(df):
            calls.append("second")
            return True

        rule = Rule(name="short-circuit", conditions=[first, second])
        rule.evaluate(_make_df(close=[1.0]))
        assert calls == ["first"]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class TestEngine:
    def test_returns_match_for_matching_rule(self, crossover_df):
        """run() returns one RuleMatch for a rule whose conditions are met."""
        rule = Rule(
            name="EMA Crossover",
            conditions=[partial(ema_crossover, fast=9, slow=21)],
        )
        matches = run([rule], crossover_df, "BTC/USDT", "4h")
        assert len(matches) == 1
        assert isinstance(matches[0], RuleMatch)

    def test_returns_empty_list_when_no_rules_match(self, crossover_df):
        """run() returns [] when no rules fire."""
        rule = Rule(name="Never fires", conditions=[lambda df: False])
        assert run([rule], crossover_df, "BTC/USDT", "4h") == []

    def test_returns_empty_list_for_empty_rules(self, crossover_df):
        assert run([], crossover_df, "BTC/USDT", "4h") == []

    def test_match_contains_correct_symbol(self, crossover_df):
        rule = Rule(name="R", conditions=[lambda df: True])
        match = run([rule], crossover_df, "ETH/USDT", "1d")[0]
        assert match.symbol == "ETH/USDT"

    def test_match_contains_correct_timeframe(self, crossover_df):
        rule = Rule(name="R", conditions=[lambda df: True])
        match = run([rule], crossover_df, "BTC/USDT", "1d")[0]
        assert match.timeframe == "1d"

    def test_match_message_falls_back_to_rule_name(self, crossover_df):
        """Unknown rule names produce the rule name as the message."""
        rule = Rule(name="My Rule", conditions=[lambda df: True])
        match = run([rule], crossover_df, "BTC/USDT", "4h")[0]
        assert match.message == "My Rule"

    def test_known_rule_produces_rich_message(self, crossover_df):
        """Known rule names produce a descriptive message and populate indicators."""
        crossover_df["rsi"] = 42.0  # synthetic value
        rule = Rule(name="RSI Oversold", conditions=[lambda df: True])
        match = run([rule], crossover_df, "BTC/USDT", "4h")[0]
        assert "oversold" in match.message.lower()
        assert match.indicators.get("rsi") == pytest.approx(42.0)

    def test_only_matching_rules_returned(self, crossover_df):
        """With 3 rules where 2 match and 1 doesn't, only 2 RuleMatches returned."""
        rules = [
            Rule(name="fires", conditions=[lambda df: True]),
            Rule(name="silent", conditions=[lambda df: False]),
            Rule(name="also fires", conditions=[lambda df: True]),
        ]
        matches = run(rules, crossover_df, "BTC/USDT", "4h")
        assert len(matches) == 2
        assert {m.rule.name for m in matches} == {"fires", "also fires"}
