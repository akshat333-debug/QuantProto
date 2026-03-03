"""Contract tests for MCP tools — Phase F8 validation.

Tests that each MCP tool:
1. Accepts valid input → returns correct output keys
2. Rejects invalid input → raises structured error
"""

from __future__ import annotations

import numpy as np
import pytest

from quantproto.mcp.server import (
    health,
    compute_momentum,
    compute_mean_reversion,
    compute_volatility,
    compute_composite_signal,
    compute_var,
    compute_cvar,
    compute_sharpe,
    compute_sortino,
    compute_beta,
    compute_concentration,
    risk_gate,
    run_backtest,
    bootstrap_sharpe_ci,
    detect_regime,
    rate_limiter,
)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure rate limiter doesn't interfere with tests."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def sample_price_dict():
    """Simple price dict for 3 tickers, 100 days."""
    np.random.seed(42)
    tickers = ["A", "B", "C"]
    result = {}
    for t in tickers:
        prices = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.02, 100)))
        result[t] = prices.tolist()
    return result


@pytest.fixture
def sample_return_list():
    np.random.seed(42)
    return np.random.normal(0.001, 0.02, 200).tolist()


# ── Health ────────────────────────────────────────────────────────────

class TestHealthContract:
    def test_returns_ok(self):
        result = health()
        assert result == {"status": "ok"}


# ── Alpha tool contracts ──────────────────────────────────────────────

class TestAlphaToolContracts:
    def test_momentum_returns_factor_key(self, sample_price_dict):
        result = compute_momentum(sample_price_dict, lookback=10)
        assert "factor" in result
        assert set(result["factor"].keys()) == set(sample_price_dict.keys())

    def test_mean_reversion_returns_factor_key(self, sample_price_dict):
        result = compute_mean_reversion(sample_price_dict, lookback=10)
        assert "factor" in result

    def test_volatility_returns_factor_key(self, sample_price_dict):
        # Convert prices to returns for volatility
        returns = {}
        for t, prices in sample_price_dict.items():
            r = [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))]
            returns[t] = r
        result = compute_volatility(returns, window=10)
        assert "factor" in result

    def test_composite_returns_signal_key(self, sample_price_dict):
        factors = {"mom": sample_price_dict, "mr": sample_price_dict}
        result = compute_composite_signal(factors)
        assert "signal" in result

    def test_momentum_invalid_lookback(self, sample_price_dict):
        with pytest.raises(ValueError):
            compute_momentum(sample_price_dict, lookback=-1)

    def test_momentum_empty_prices(self):
        with pytest.raises(ValueError):
            compute_momentum({}, lookback=10)


# ── Risk tool contracts ───────────────────────────────────────────────

class TestRiskToolContracts:
    def test_var_returns_var_key(self, sample_return_list):
        result = compute_var(sample_return_list, confidence=0.95)
        assert "var" in result
        assert isinstance(result["var"], float)

    def test_cvar_returns_cvar_key(self, sample_return_list):
        result = compute_cvar(sample_return_list)
        assert "cvar" in result

    def test_sharpe_returns_sharpe_key(self, sample_return_list):
        result = compute_sharpe(sample_return_list)
        assert "sharpe" in result

    def test_sortino_returns_sortino_key(self, sample_return_list):
        result = compute_sortino(sample_return_list)
        assert "sortino" in result

    def test_beta_returns_beta_key(self, sample_return_list):
        result = compute_beta(sample_return_list, sample_return_list)
        assert "beta" in result
        assert abs(result["beta"] - 1.0) < 1e-10

    def test_concentration_returns_hhi_key(self):
        result = compute_concentration([0.5, 0.3, 0.2])
        assert "hhi" in result

    def test_risk_gate_returns_passed_and_violations(self):
        result = risk_gate(
            {"sharpe": 0.5},
            {"sharpe": {"min": 1.0}},
        )
        assert "passed" in result
        assert "violations" in result
        assert result["passed"] is False

    def test_var_invalid_confidence(self, sample_return_list):
        with pytest.raises(ValueError):
            compute_var(sample_return_list, confidence=1.5)

    def test_var_empty_returns(self):
        with pytest.raises(ValueError):
            compute_var([], confidence=0.95)


# ── Backtest + regime contracts ───────────────────────────────────────

class TestBacktestRegimeContracts:
    def test_backtest_returns_required_keys(self, sample_price_dict):
        result = run_backtest(sample_price_dict, train_window=30, test_window=10)
        assert "returns" in result
        assert "equity_curve" in result
        assert "n_splits" in result
        assert isinstance(result["n_splits"], int)
        assert result["n_splits"] > 0

    def test_bootstrap_returns_required_keys(self, sample_return_list):
        result = bootstrap_sharpe_ci(sample_return_list, n_boot=100, ci=0.95, seed=42)
        assert set(result.keys()) == {"point_estimate", "ci_lower", "ci_upper"}

    def test_regime_returns_required_keys(self, sample_return_list):
        long_returns = (sample_return_list * 3)[:500]  # need enough data for HMM
        result = detect_regime(long_returns, window=20, seed=42)
        assert "states" in result
        assert "confidence" in result
        assert len(result["states"]) == len(result["confidence"])

    def test_backtest_invalid_window(self, sample_price_dict):
        with pytest.raises(ValueError):
            run_backtest(sample_price_dict, train_window=0, test_window=10)
