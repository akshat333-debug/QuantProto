"""Tests for WalkForwardBacktester — Phase D validation."""

import numpy as np
import pandas as pd
import pytest

from quantproto.walk_forward import WalkForwardBacktester


# ── Window splitting ──────────────────────────────────────────────────

class TestSplitWindows:
    def test_expected_number_of_splits(self):
        splits = WalkForwardBacktester._split_windows(200, 60, 20)
        # (200 - 60) / 20 = 7 splits
        assert len(splits) == 7

    def test_no_train_test_overlap(self):
        """Train end must equal test start (no gap, no overlap)."""
        splits = WalkForwardBacktester._split_windows(200, 60, 20)
        for train_start, train_end, test_start, test_end in splits:
            assert train_end == test_start, "Train/test must be contiguous"
            assert train_start < train_end
            assert test_start < test_end

    def test_no_future_leakage(self):
        """Train period must never exceed test start."""
        splits = WalkForwardBacktester._split_windows(200, 60, 20)
        for train_start, train_end, test_start, test_end in splits:
            assert train_end <= test_start

    def test_raises_on_too_large_windows(self):
        with pytest.raises(ValueError):
            WalkForwardBacktester._split_windows(50, 40, 20)


# ── Backtest run ──────────────────────────────────────────────────────

class TestRun:
    @staticmethod
    def _equal_weight_signal(prices: pd.DataFrame) -> pd.DataFrame:
        """Trivial signal: equal weight across all assets."""
        return pd.DataFrame(
            np.ones_like(prices.values) / prices.shape[1],
            index=prices.index,
            columns=prices.columns,
        )

    def test_returns_length(self, sample_prices):
        result = WalkForwardBacktester.run(
            sample_prices,
            self._equal_weight_signal,
            train_window=60,
            test_window=20,
        )
        # returns from pct_change drops 1 row → n=199
        # splits = (199-60)/20 = 6 full + remainder check
        expected_test_days = result["n_splits"] * 20
        assert len(result["returns"]) == expected_test_days

    def test_equity_curve_starts_near_one(self, sample_prices):
        result = WalkForwardBacktester.run(
            sample_prices,
            self._equal_weight_signal,
            train_window=60,
            test_window=20,
        )
        # First value of equity curve = 1 + first return ≈ 1.0
        assert abs(result["equity_curve"].iloc[0] - 1.0) < 0.1

    def test_equity_curve_length_matches_returns(self, sample_prices):
        result = WalkForwardBacktester.run(
            sample_prices,
            self._equal_weight_signal,
            train_window=60,
            test_window=20,
        )
        assert len(result["equity_curve"]) == len(result["returns"])


# ── Equity curve ──────────────────────────────────────────────────────

class TestEquityCurve:
    def test_starts_near_one(self):
        returns = pd.Series([0.01, -0.005, 0.02, 0.0, -0.01])
        eq = WalkForwardBacktester.equity_curve(returns)
        assert abs(eq.iloc[0] - 1.01) < 1e-10

    def test_length(self):
        returns = pd.Series(np.random.normal(0, 0.01, 100))
        eq = WalkForwardBacktester.equity_curve(returns)
        assert len(eq) == 100

    def test_numpy_input(self):
        returns = np.array([0.01, 0.02, -0.01])
        eq = WalkForwardBacktester.equity_curve(returns)
        assert len(eq) == 3


# ── Bootstrap Sharpe CI ──────────────────────────────────────────────

class TestBootstrapSharpeCI:
    def test_ci_bounds_order(self):
        """lower < point_estimate < upper for normal data."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)
        result = WalkForwardBacktester.bootstrap_sharpe_ci(returns, n_boot=500)
        assert result["ci_lower"] < result["point_estimate"] < result["ci_upper"]

    def test_deterministic(self):
        """Same seed → same CI."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 500)
        r1 = WalkForwardBacktester.bootstrap_sharpe_ci(returns, seed=42)
        r2 = WalkForwardBacktester.bootstrap_sharpe_ci(returns, seed=42)
        assert r1 == r2

    def test_output_keys(self):
        returns = np.random.normal(0, 0.01, 100)
        result = WalkForwardBacktester.bootstrap_sharpe_ci(returns, n_boot=100)
        assert set(result.keys()) == {"point_estimate", "ci_lower", "ci_upper"}

    def test_wider_ci_with_fewer_data(self):
        """Less data → wider CI."""
        np.random.seed(42)
        long_returns = np.random.normal(0.001, 0.02, 1000)
        short_returns = long_returns[:50]
        ci_long = WalkForwardBacktester.bootstrap_sharpe_ci(long_returns, n_boot=500, seed=42)
        ci_short = WalkForwardBacktester.bootstrap_sharpe_ci(short_returns, n_boot=500, seed=42)
        width_long = ci_long["ci_upper"] - ci_long["ci_lower"]
        width_short = ci_short["ci_upper"] - ci_short["ci_lower"]
        assert width_short > width_long
