"""Tests for Multi-Timeframe Signals (T1.5)."""

import numpy as np
import pandas as pd
import pytest

from quantproto.factors import MultiTimeframe


@pytest.fixture
def daily_prices():
    np.random.seed(42)
    dates = pd.bdate_range("2022-01-03", periods=300)
    data = {}
    for t in ["A", "B", "C"]:
        data[t] = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.02, 300)))
    return pd.DataFrame(data, index=dates)


class TestResample:
    def test_weekly(self, daily_prices):
        mtf = MultiTimeframe()
        weekly = mtf.resample_prices(daily_prices, "weekly")
        assert len(weekly) < len(daily_prices)

    def test_monthly(self, daily_prices):
        mtf = MultiTimeframe()
        monthly = mtf.resample_prices(daily_prices, "monthly")
        assert len(monthly) < len(daily_prices) // 15


class TestMultiTFMomentum:
    def test_output_shape(self, daily_prices):
        mtf = MultiTimeframe()
        signal = mtf.multi_tf_momentum(daily_prices)
        assert signal.shape[1] == daily_prices.shape[1]

    def test_bounded(self, daily_prices):
        mtf = MultiTimeframe()
        signal = mtf.multi_tf_momentum(daily_prices)
        valid = signal.dropna()
        assert valid.max().max() <= 1.0 + 1e-6
        assert valid.min().min() >= 0.0 - 1e-6


class TestAdaptiveLookback:
    def test_returns_dict(self, daily_prices):
        mtf = MultiTimeframe()
        lookbacks = mtf.adaptive_lookback(daily_prices, lookback_range=(10, 30), step=10)
        assert isinstance(lookbacks, dict)
        assert set(lookbacks.keys()) == set(daily_prices.columns)

    def test_within_range(self, daily_prices):
        mtf = MultiTimeframe()
        lookbacks = mtf.adaptive_lookback(daily_prices, lookback_range=(10, 50), step=10)
        for lb in lookbacks.values():
            assert 10 <= lb <= 50
