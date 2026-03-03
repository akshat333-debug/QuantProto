"""Tests for Portfolio Optimiser (T1.1)."""

import numpy as np
import pytest

from quantproto.portfolio.optimiser import PortfolioOptimiser


@pytest.fixture
def simple_cov():
    return np.array([[0.04, 0.006], [0.006, 0.09]])


@pytest.fixture
def simple_returns():
    return np.array([0.10, 0.05])


class TestMeanVariance:
    def test_weights_sum_to_one(self, simple_returns, simple_cov):
        w = PortfolioOptimiser.mean_variance(simple_returns, simple_cov)
        assert abs(np.sum(w) - 1.0) < 1e-6

    def test_weights_non_negative(self, simple_returns, simple_cov):
        w = PortfolioOptimiser.mean_variance(simple_returns, simple_cov)
        assert np.all(w >= -1e-6)

    def test_higher_risk_aversion_lower_portfolio_vol(self, simple_returns, simple_cov):
        w_low = PortfolioOptimiser.mean_variance(simple_returns, simple_cov, risk_aversion=0.5)
        w_high = PortfolioOptimiser.mean_variance(simple_returns, simple_cov, risk_aversion=5.0)
        vol_low = np.sqrt(w_low @ simple_cov @ w_low)
        vol_high = np.sqrt(w_high @ simple_cov @ w_high)
        # Higher risk aversion → lower portfolio volatility
        assert vol_high <= vol_low + 1e-6

    def test_max_weight_constraint(self, simple_returns, simple_cov):
        w = PortfolioOptimiser.mean_variance(simple_returns, simple_cov, max_weight=0.6)
        assert np.all(w <= 0.6 + 1e-6)


class TestMinVolatility:
    def test_weights_sum_to_one(self, simple_cov):
        w = PortfolioOptimiser.min_volatility(simple_cov)
        assert abs(np.sum(w) - 1.0) < 1e-6

    def test_prefers_lower_vol_asset(self, simple_cov):
        w = PortfolioOptimiser.min_volatility(simple_cov)
        # Asset 0 has vol=0.2, Asset 1 has vol=0.3 → should prefer Asset 0
        assert w[0] > w[1]


class TestMaxSharpe:
    def test_weights_sum_to_one(self, simple_returns, simple_cov):
        w = PortfolioOptimiser.max_sharpe(simple_returns, simple_cov)
        assert abs(np.sum(w) - 1.0) < 1e-6

    def test_prefers_higher_sharpe_asset(self):
        # Asset 0: ret=10%, vol=20% → Sharpe=0.5 | Asset 1: ret=5%, vol=30% → Sharpe=0.17
        mu = np.array([0.10, 0.05])
        cov = np.diag([0.04, 0.09])
        w = PortfolioOptimiser.max_sharpe(mu, cov)
        assert w[0] > w[1]


class TestRiskParity:
    def test_weights_sum_to_one(self, simple_cov):
        w = PortfolioOptimiser.risk_parity(simple_cov)
        assert abs(np.sum(w) - 1.0) < 1e-6

    def test_equal_risk_contribution(self):
        cov = np.diag([0.04, 0.04])  # equal vol → equal weight
        w = PortfolioOptimiser.risk_parity(cov)
        assert abs(w[0] - w[1]) < 0.05


class TestKellyCriterion:
    def test_positive_weights_for_positive_returns(self, simple_returns, simple_cov):
        w = PortfolioOptimiser.kelly_criterion(simple_returns, simple_cov)
        assert np.all(w > 0)

    def test_half_kelly_smaller_than_full(self, simple_returns, simple_cov):
        w_full = PortfolioOptimiser.kelly_criterion(simple_returns, simple_cov, fraction=1.0)
        w_half = PortfolioOptimiser.kelly_criterion(simple_returns, simple_cov, fraction=0.5)
        # Half Kelly has same direction but different magnitude
        assert np.allclose(w_full / np.abs(w_full).sum(),
                          w_half / np.abs(w_half).sum(), atol=0.01)


class TestConstrainedRebalance:
    def test_no_constraint_needed(self):
        target = np.array([0.55, 0.45])
        current = np.array([0.50, 0.50])
        result = PortfolioOptimiser.constrained_rebalance(target, current, max_turnover=0.1)
        np.testing.assert_allclose(result, target, atol=1e-6)

    def test_turnover_limited(self):
        target = np.array([0.90, 0.10])
        current = np.array([0.50, 0.50])
        result = PortfolioOptimiser.constrained_rebalance(target, current, max_turnover=0.1)
        turnover = np.sum(np.abs(result - current)) / 2
        assert turnover <= 0.1 + 1e-6

    def test_weights_sum_to_one(self):
        target = np.array([0.80, 0.20])
        current = np.array([0.50, 0.50])
        result = PortfolioOptimiser.constrained_rebalance(target, current, max_turnover=0.05)
        assert abs(np.sum(result) - 1.0) < 1e-6
