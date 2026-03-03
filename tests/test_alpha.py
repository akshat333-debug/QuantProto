"""Tests for FactorAlphaEngine — Phase A validation."""

import numpy as np
import pandas as pd
import pytest

from quantproto.factor_engine import FactorAlphaEngine


# ── Momentum ──────────────────────────────────────────────────────────

class TestMomentumFactor:
    def test_shape_matches_input(self, sample_prices):
        engine = FactorAlphaEngine()
        result = engine.momentum_factor(sample_prices, lookback=20)
        assert result.shape == sample_prices.shape

    def test_no_nans_after_lookback(self, sample_prices):
        lookback = 20
        result = FactorAlphaEngine.momentum_factor(sample_prices, lookback=lookback)
        after_warmup = result.iloc[lookback:]
        assert not after_warmup.isna().any().any(), "NaNs found after lookback window"

    def test_index_preserved(self, sample_prices):
        result = FactorAlphaEngine.momentum_factor(sample_prices)
        pd.testing.assert_index_equal(result.index, sample_prices.index)

    def test_columns_preserved(self, sample_prices):
        result = FactorAlphaEngine.momentum_factor(sample_prices)
        pd.testing.assert_index_equal(result.columns, sample_prices.columns)


# ── Mean Reversion ────────────────────────────────────────────────────

class TestMeanReversionFactor:
    def test_shape_matches_input(self, sample_prices):
        result = FactorAlphaEngine.mean_reversion_factor(sample_prices, lookback=20)
        assert result.shape == sample_prices.shape

    def test_zscore_centered_near_zero(self, sample_prices):
        """For GBM-generated data, z-scores should be roughly centered."""
        result = FactorAlphaEngine.mean_reversion_factor(sample_prices, lookback=20)
        valid = result.dropna()
        mean_zscore = valid.values.mean()
        assert abs(mean_zscore) < 0.5, f"Mean z-score too far from 0: {mean_zscore}"

    def test_no_nans_after_lookback(self, sample_prices):
        lookback = 20
        result = FactorAlphaEngine.mean_reversion_factor(sample_prices, lookback=lookback)
        # rolling(20) needs 19 NaN rows; pct_change is internal so lookback-1
        after_warmup = result.iloc[lookback:]
        assert not after_warmup.isna().any().any()


# ── Volatility ────────────────────────────────────────────────────────

class TestVolatilityFactor:
    def test_shape_matches_input(self, sample_returns):
        result = FactorAlphaEngine.volatility_factor(sample_returns, window=20)
        assert result.shape == sample_returns.shape

    def test_positive_after_warmup(self, sample_returns):
        window = 20
        result = FactorAlphaEngine.volatility_factor(sample_returns, window=window)
        valid = result.iloc[window:]
        assert (valid > 0).all().all(), "Volatility must be positive after warmup"

    def test_no_nans_after_warmup(self, sample_returns):
        window = 20
        result = FactorAlphaEngine.volatility_factor(sample_returns, window=window)
        after_warmup = result.iloc[window:]
        assert not after_warmup.isna().any().any()


# ── Composite Signal ─────────────────────────────────────────────────

class TestCompositeSignal:
    @pytest.fixture
    def factor_inputs(self, sample_prices, sample_returns):
        """Build factor dict for composite signal testing."""
        engine = FactorAlphaEngine()
        return {
            "momentum": engine.momentum_factor(sample_prices, lookback=20),
            "mean_reversion": engine.mean_reversion_factor(sample_prices, lookback=20),
            "volatility": engine.volatility_factor(sample_returns, window=20),
        }

    def test_output_bounds(self, factor_inputs):
        result = FactorAlphaEngine.composite_signal(factor_inputs)
        assert (result.values >= 0).all(), "Signal below 0"
        assert (result.values <= 1).all(), "Signal above 1"

    def test_output_shape(self, factor_inputs):
        result = FactorAlphaEngine.composite_signal(factor_inputs)
        # Output rows = intersection of all factor indices
        common_idx = list(factor_inputs.values())[0].index
        for df in factor_inputs.values():
            common_idx = common_idx.intersection(df.index)
        expected_cols = list(factor_inputs.values())[0].columns
        assert result.shape == (len(common_idx), len(expected_cols))

    def test_deterministic(self, factor_inputs):
        """Two calls with identical input must produce identical output."""
        r1 = FactorAlphaEngine.composite_signal(factor_inputs)
        r2 = FactorAlphaEngine.composite_signal(factor_inputs)
        pd.testing.assert_frame_equal(r1, r2)

    def test_custom_weights(self, factor_inputs):
        weights = {"momentum": 0.5, "mean_reversion": 0.3, "volatility": 0.2}
        result = FactorAlphaEngine.composite_signal(factor_inputs, weights=weights)
        assert (result.values >= 0).all()
        assert (result.values <= 1).all()
