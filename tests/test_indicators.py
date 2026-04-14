"""Tests for candle.indicators — trend, momentum, and volume indicators.

All tests use stable CSV fixtures with known inputs and expected outputs.
No random data. No real exchange calls.
"""

import numpy as np
import pandas as pd
import pytest

from candle.indicators.trend import ema, sma, macd
from candle.indicators.momentum import rsi, stochastic
from candle.indicators.volume import vwap, obv, cvd


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def btc_4h() -> pd.DataFrame:
    """Load 100-candle BTC/USDT 4h fixture."""
    return pd.read_csv("tests/fixtures/btc_4h_100.csv", parse_dates=["timestamp"])


@pytest.fixture
def btc_crossover() -> pd.DataFrame:
    """Load fixture containing a known EMA(9)/EMA(21) crossover on the last candle."""
    return pd.read_csv("tests/fixtures/btc_4h_crossover.csv", parse_dates=["timestamp"])


@pytest.fixture
def btc_overbought() -> pd.DataFrame:
    """Load fixture where RSI(14) > 70 on the last candle."""
    return pd.read_csv("tests/fixtures/btc_4h_overbought.csv", parse_dates=["timestamp"])


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------

class TestEma:
    def test_returns_series_of_same_length(self, btc_4h):
        result = ema(btc_4h, period=9)
        assert len(result) == len(btc_4h)

    def test_leading_values_are_nan(self, btc_4h):
        period = 9
        result = ema(btc_4h, period=period)
        assert result.iloc[: period - 1].isna().all()
        assert result.iloc[period - 1 :].notna().all()

    def test_period_1_equals_source_column(self, btc_4h):
        result = ema(btc_4h, period=1)
        pd.testing.assert_series_equal(result, btc_4h["close"], check_names=False)

    def test_custom_column(self, btc_4h):
        result = ema(btc_4h, period=5, column="volume")
        assert result.notna().any()
        assert len(result) == len(btc_4h)


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------

class TestSma:
    def test_returns_series_of_same_length(self, btc_4h):
        result = sma(btc_4h, period=9)
        assert len(result) == len(btc_4h)

    def test_leading_values_are_nan(self, btc_4h):
        period = 9
        result = sma(btc_4h, period=period)
        assert result.iloc[: period - 1].isna().all()
        assert result.iloc[period - 1 :].notna().all()

    def test_value_equals_manual_mean(self, btc_4h):
        period = 5
        result = sma(btc_4h, period=period)
        expected = btc_4h["close"].iloc[4:9].mean()
        assert abs(result.iloc[8] - expected) < 1e-8


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------

class TestMacd:
    def test_returns_dataframe_with_three_columns(self, btc_4h):
        result = macd(btc_4h)
        assert list(result.columns) == ["macd", "macd_signal", "macd_histogram"]

    def test_same_index_as_input(self, btc_4h):
        result = macd(btc_4h)
        assert len(result) == len(btc_4h)

    def test_histogram_equals_macd_minus_signal(self, btc_4h):
        result = macd(btc_4h)
        diff = (result["macd_histogram"] - (result["macd"] - result["macd_signal"])).dropna()
        assert (diff.abs() < 1e-10).all()

    def test_leading_nan_from_slow_period(self, btc_4h):
        # With slow=26, the macd line needs 26 candles before it's valid.
        result = macd(btc_4h, fast=12, slow=26, signal=9)
        assert result["macd"].iloc[:25].isna().all()
        assert result["macd"].iloc[25:].notna().all()


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------

class TestRsi:
    def test_returns_series_of_same_length(self, btc_4h):
        result = rsi(btc_4h)
        assert len(result) == len(btc_4h)

    def test_values_in_range_0_to_100(self, btc_4h):
        result = rsi(btc_4h).dropna()
        assert (result >= 0).all() and (result <= 100).all()

    def test_detects_overbought_in_fixture(self, btc_overbought):
        result = rsi(btc_overbought)
        assert result.iloc[-1] > 70

    def test_leading_values_are_nan(self, btc_4h):
        period = 14
        result = rsi(btc_4h, period=period)
        assert result.iloc[:period].isna().all()
        assert result.iloc[period:].notna().all()


# ---------------------------------------------------------------------------
# Stochastic
# ---------------------------------------------------------------------------

class TestStochastic:
    def test_returns_dataframe_with_two_columns(self, btc_4h):
        result = stochastic(btc_4h)
        assert list(result.columns) == ["stoch_k", "stoch_d"]

    def test_same_index_as_input(self, btc_4h):
        result = stochastic(btc_4h)
        assert len(result) == len(btc_4h)

    def test_k_values_in_range_0_to_100(self, btc_4h):
        result = stochastic(btc_4h)["stoch_k"].dropna()
        assert (result >= 0).all() and (result <= 100).all()

    def test_d_values_in_range_0_to_100(self, btc_4h):
        result = stochastic(btc_4h)["stoch_d"].dropna()
        assert (result >= 0).all() and (result <= 100).all()


# ---------------------------------------------------------------------------
# VWAP
# ---------------------------------------------------------------------------

class TestVwap:
    def test_no_nan_values(self, btc_4h):
        result = vwap(btc_4h)
        assert result.isna().sum() == 0

    def test_same_length_as_input(self, btc_4h):
        result = vwap(btc_4h)
        assert len(result) == len(btc_4h)

    def test_within_global_price_range(self, btc_4h):
        # Cumulative VWAP lies within the dataset's overall high/low range,
        # not necessarily within any single candle's range.
        result = vwap(btc_4h)
        assert (result >= btc_4h["low"].min()).all()
        assert (result <= btc_4h["high"].max()).all()

    def test_first_value_equals_typical_price(self, btc_4h):
        # On the first candle, VWAP == typical price exactly.
        result = vwap(btc_4h)
        row = btc_4h.iloc[0]
        expected = (row["high"] + row["low"] + row["close"]) / 3
        assert abs(result.iloc[0] - expected) < 1e-8


# ---------------------------------------------------------------------------
# OBV
# ---------------------------------------------------------------------------

class TestObv:
    def test_returns_series_of_same_length(self, btc_4h):
        result = obv(btc_4h)
        assert len(result) == len(btc_4h)

    def test_increases_on_up_candle(self, btc_4h):
        result = obv(btc_4h)
        for i in range(1, len(btc_4h)):
            if btc_4h["close"].iloc[i] > btc_4h["close"].iloc[i - 1]:
                assert result.iloc[i] > result.iloc[i - 1]

    def test_decreases_on_down_candle(self, btc_4h):
        result = obv(btc_4h)
        for i in range(1, len(btc_4h)):
            if btc_4h["close"].iloc[i] < btc_4h["close"].iloc[i - 1]:
                assert result.iloc[i] < result.iloc[i - 1]


# ---------------------------------------------------------------------------
# CVD
# ---------------------------------------------------------------------------

class TestCvd:
    def test_returns_series_of_same_length(self, btc_4h):
        result = cvd(btc_4h)
        assert len(result) == len(btc_4h)

    def test_delta_positive_on_bullish_candle(self, btc_4h):
        result = cvd(btc_4h)
        for i in range(1, len(btc_4h)):
            if btc_4h["close"].iloc[i] > btc_4h["open"].iloc[i]:
                delta = result.iloc[i] - result.iloc[i - 1]
                assert delta > 0

    def test_delta_negative_on_bearish_candle(self, btc_4h):
        result = cvd(btc_4h)
        for i in range(1, len(btc_4h)):
            if btc_4h["close"].iloc[i] < btc_4h["open"].iloc[i]:
                delta = result.iloc[i] - result.iloc[i - 1]
                assert delta < 0
