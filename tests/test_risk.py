"""Tests for RiskEngine — Phase B validation."""

import numpy as np
import pytest

from quantproto.risk_engine import RiskEngine


class TestValueAtRisk:
    def test_var_negative_for_negative_drift(self):
        """VaR should be negative for a series with negative mean."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.02, 500)
        var = RiskEngine.value_at_risk(returns, confidence=0.95)
        assert var < 0, f"VaR should be negative, got {var}"

    def test_var_is_scalar(self, sample_returns):
        col = sample_returns.iloc[:, 0]
        var = RiskEngine.value_at_risk(col)
        assert isinstance(var, float)


class TestCVaR:
    def test_cvar_leq_var(self):
        """CVaR (expected shortfall) must be ≤ VaR."""
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, 1000)
        var = RiskEngine.value_at_risk(returns, confidence=0.95)
        cvar = RiskEngine.cvar(returns, confidence=0.95)
        assert cvar <= var, f"CVaR {cvar} must be ≤ VaR {var}"


class TestSharpeRatio:
    def test_positive_for_positive_drift(self):
        """Sharpe should be > 0 for a positive-drift series."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 500)
        sharpe = RiskEngine.sharpe_ratio(returns)
        assert sharpe > 0, f"Sharpe should be positive, got {sharpe}"

    def test_zero_for_constant_returns(self):
        returns = np.full(100, 0.001)
        sharpe = RiskEngine.sharpe_ratio(returns)
        # constant returns → std=0 → should return 0
        assert sharpe == 0.0


class TestSortinoRatio:
    def test_sortino_geq_sharpe_when_downside_smaller(self):
        """When downside vol < total vol, Sortino ≥ Sharpe."""
        np.random.seed(42)
        # Create positive-drift series with asymmetric volatility
        base = np.random.normal(0.002, 0.01, 500)
        # Add occasional small drawdowns (downside vol < total vol)
        base[::5] = -0.003
        sharpe = RiskEngine.sharpe_ratio(base)
        sortino = RiskEngine.sortino_ratio(base)
        assert sortino >= sharpe, f"Sortino {sortino} should ≥ Sharpe {sharpe}"

    def test_sortino_inf_for_no_downside(self):
        """All positive returns → Sortino = inf."""
        returns = np.abs(np.random.normal(0.001, 0.01, 100)) + 0.0001
        sortino = RiskEngine.sortino_ratio(returns)
        assert sortino == float('inf')


class TestBeta:
    def test_beta_one_for_identical_series(self):
        """Beta of a series against itself should be ≈ 1.0."""
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, 500)
        b = RiskEngine.beta(returns, returns)
        assert abs(b - 1.0) < 1e-10, f"Beta should be 1.0, got {b}"

    def test_beta_is_scalar(self, sample_returns):
        r = sample_returns.iloc[:, 0].values
        bench = sample_returns.iloc[:, 1].values
        b = RiskEngine.beta(r, bench)
        assert isinstance(b, float)


class TestConcentrationRisk:
    def test_hhi_single_asset(self):
        """100 % in one asset → HHI = 1.0."""
        weights = np.array([1.0])
        assert RiskEngine.concentration_risk(weights) == pytest.approx(1.0)

    def test_hhi_equal_weight(self):
        """Equal weight across 5 assets → HHI = 0.2."""
        weights = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
        assert RiskEngine.concentration_risk(weights) == pytest.approx(0.2)

    def test_hhi_two_assets(self):
        weights = np.array([0.7, 0.3])
        expected = 0.7**2 + 0.3**2  # 0.58
        assert RiskEngine.concentration_risk(weights) == pytest.approx(expected)


class TestRiskGate:
    def test_passes_within_thresholds(self):
        metrics = {"var": -0.02, "sharpe": 1.5}
        thresholds = {
            "var": {"min": -0.05},
            "sharpe": {"min": 0.5},
        }
        result = RiskEngine.risk_gate(metrics, thresholds)
        assert result["passed"] is True
        assert len(result["violations"]) == 0

    def test_fails_on_violation(self):
        metrics = {"var": -0.10, "sharpe": 0.2}
        thresholds = {
            "var": {"min": -0.05},
            "sharpe": {"min": 0.5},
        }
        result = RiskEngine.risk_gate(metrics, thresholds)
        assert result["passed"] is False
        assert len(result["violations"]) == 2

    def test_max_threshold(self):
        metrics = {"drawdown": -0.3}
        thresholds = {"drawdown": {"max": -0.2}}
        result = RiskEngine.risk_gate(metrics, thresholds)
        # -0.3 is not > -0.2, so this should pass
        assert result["passed"] is True

    def test_violations_have_correct_keys(self):
        metrics = {"sharpe": 0.1}
        thresholds = {"sharpe": {"min": 1.0}}
        result = RiskEngine.risk_gate(metrics, thresholds)
        assert result["passed"] is False
        v = result["violations"][0]
        assert set(v.keys()) == {"metric", "value", "rule", "limit"}
