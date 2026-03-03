"""Tests for Drawdown Analytics (T1.2)."""

import numpy as np
import pandas as pd
import pytest

from quantproto.analytics import DrawdownAnalytics


@pytest.fixture
def equity_with_drawdown():
    return np.array([1.0, 1.05, 1.10, 1.03, 0.95, 0.98, 1.02, 1.12, 1.08, 1.15])


class TestDrawdownSeries:
    def test_starts_at_zero(self, equity_with_drawdown):
        dd = DrawdownAnalytics.drawdown_series(equity_with_drawdown)
        assert dd[0] == 0.0

    def test_always_non_positive(self, equity_with_drawdown):
        dd = DrawdownAnalytics.drawdown_series(equity_with_drawdown)
        assert np.all(dd <= 1e-10)

    def test_pandas_input(self, equity_with_drawdown):
        series = pd.Series(equity_with_drawdown)
        dd = DrawdownAnalytics.drawdown_series(series)
        assert isinstance(dd, pd.Series)


class TestMaxDrawdown:
    def test_negative(self, equity_with_drawdown):
        mdd = DrawdownAnalytics.max_drawdown(equity_with_drawdown)
        assert mdd < 0

    def test_known_value(self):
        eq = np.array([1.0, 2.0, 1.5])
        mdd = DrawdownAnalytics.max_drawdown(eq)
        assert abs(mdd - (-0.25)) < 1e-6

    def test_no_drawdown(self):
        eq = np.array([1.0, 2.0, 3.0, 4.0])
        mdd = DrawdownAnalytics.max_drawdown(eq)
        assert mdd == 0.0


class TestCalmarRatio:
    def test_positive_for_positive_returns(self, equity_with_drawdown):
        returns = np.diff(equity_with_drawdown) / equity_with_drawdown[:-1]
        calmar = DrawdownAnalytics.calmar_ratio(returns, equity_with_drawdown)
        assert calmar > 0

    def test_zero_for_no_drawdown(self):
        eq = np.array([1.0, 1.01, 1.02, 1.03])
        returns = np.diff(eq) / eq[:-1]
        calmar = DrawdownAnalytics.calmar_ratio(returns, eq)
        assert calmar == 0.0
        # Actually this will have a tiny drawdown, let me adjust
        # With monotonically increasing equity, max_dd = 0 → calmar = 0


class TestPainIndex:
    def test_non_negative(self, equity_with_drawdown):
        pi = DrawdownAnalytics.pain_index(equity_with_drawdown)
        assert pi >= 0

    def test_zero_for_monotonic(self):
        eq = np.array([1.0, 2.0, 3.0])
        pi = DrawdownAnalytics.pain_index(eq)
        assert pi == 0.0


class TestUnderwaterPeriods:
    def test_finds_drawdown_period(self, equity_with_drawdown):
        periods = DrawdownAnalytics.underwater_periods(equity_with_drawdown)
        assert len(periods) >= 1

    def test_period_has_required_keys(self, equity_with_drawdown):
        periods = DrawdownAnalytics.underwater_periods(equity_with_drawdown)
        for p in periods:
            assert "start" in p and "trough" in p and "end" in p
            assert "depth" in p and "duration" in p
            assert p["depth"] < 0


class TestDrawdownPositionScale:
    def test_scales_down_in_drawdown(self):
        eq = np.array([1.0, 1.1, 1.0, 0.85, 0.80, 0.90, 1.0])
        scales = DrawdownAnalytics.drawdown_position_scale(eq, max_dd_threshold=-0.10)
        # At point 4 (0.80), drawdown from peak 1.1 = -27%, should scale down
        assert scales[4] < 1.0

    def test_no_scaling_above_threshold(self):
        eq = np.array([1.0, 1.05, 1.03, 1.04])
        scales = DrawdownAnalytics.drawdown_position_scale(eq)
        assert np.all(scales == 1.0)
