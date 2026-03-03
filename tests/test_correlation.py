"""Tests for Correlation + Clustering Engine (T2.1)."""

import numpy as np
import pandas as pd
import pytest

from quantproto.analytics.correlation import CorrelationEngine


@pytest.fixture
def multi_asset_returns():
    np.random.seed(42)
    dates = pd.bdate_range("2023-01-01", periods=200)
    data = {
        "A": np.random.normal(0.001, 0.02, 200),
        "B": np.random.normal(0.0005, 0.025, 200),
        "C": np.random.normal(0.0008, 0.018, 200),
    }
    return pd.DataFrame(data, index=dates)


class TestRollingCorrelation:
    def test_output_length(self, multi_asset_returns):
        corr = CorrelationEngine.rolling_correlation(multi_asset_returns, window=30)
        assert len(corr) == len(multi_asset_returns) - 30 + 1

    def test_bounded(self, multi_asset_returns):
        corr = CorrelationEngine.rolling_correlation(multi_asset_returns, window=30)
        assert corr.max() <= 1.0 + 1e-6
        assert corr.min() >= -1.0 - 1e-6


class TestPCA:
    def test_returns_required_keys(self, multi_asset_returns):
        result = CorrelationEngine.pca_decomposition(multi_asset_returns, n_components=2)
        assert "eigenvalues" in result
        assert "eigenvectors" in result
        assert "explained_variance_ratio" in result
        assert "loadings" in result

    def test_explained_variance_sums_to_less_than_one(self, multi_asset_returns):
        result = CorrelationEngine.pca_decomposition(multi_asset_returns, n_components=2)
        assert sum(result["explained_variance_ratio"]) <= 1.0 + 1e-6

    def test_loadings_shape(self, multi_asset_returns):
        result = CorrelationEngine.pca_decomposition(multi_asset_returns, n_components=2)
        assert result["loadings"].shape == (3, 2)


class TestHRP:
    def test_weights_sum_to_one(self):
        cov = np.diag([0.04, 0.09, 0.01])
        w = CorrelationEngine.hierarchical_risk_parity(cov)
        assert abs(np.sum(w) - 1.0) < 1e-6

    def test_non_negative(self):
        cov = np.array([[0.04, 0.01, 0.005],
                       [0.01, 0.09, 0.01],
                       [0.005, 0.01, 0.01]])
        w = CorrelationEngine.hierarchical_risk_parity(cov)
        assert np.all(w >= 0)


class TestCorrelationRegime:
    def test_valid_labels(self, multi_asset_returns):
        regimes = CorrelationEngine.correlation_regime(multi_asset_returns, window=30)
        valid = {"RISK_ON", "NEUTRAL", "RISK_OFF"}
        assert set(regimes.unique()).issubset(valid)
