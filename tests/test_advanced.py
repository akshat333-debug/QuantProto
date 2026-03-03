"""Tests for Advanced Regime + Event Backtest + Paper Trading + Stress + Compliance + ML + Multi-Strategy + Compute."""

import time
import numpy as np
import pandas as pd
import pytest

from quantproto.regime import EnsembleRegime
from quantproto.backtest import EventBacktester, Order, OrderType
from quantproto.trading import PaperBroker
from quantproto.risk.stress import StressTester
from quantproto.compliance import AuditLog, PreTradeCompliance
from quantproto.ml.feature_store import FeatureStore
from quantproto.ml.models import MLAlphaModel, PurgedKFold
from quantproto.strategy.multi_strategy import MultiStrategyManager
from quantproto.strategy.base import MomentumStrategy, MeanReversionStrategy


@pytest.fixture
def prices():
    np.random.seed(42)
    dates = pd.bdate_range("2022-01-03", periods=300)
    data = {}
    for t in ["A", "B", "C"]:
        data[t] = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.02, 300)))
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def returns(prices):
    return prices.pct_change().dropna()


# ── T2.2: Ensemble Regime ─────────────────────────────────────────────

class TestEnsembleRegime:
    def test_fit_predict_keys(self, returns):
        er = EnsembleRegime(seed=42)
        result = er.fit_predict(returns)
        assert "ensemble_state" in result
        assert "ensemble_score" in result
        assert "hmm_states" in result

    def test_valid_states(self, returns):
        er = EnsembleRegime(seed=42)
        result = er.fit_predict(returns)
        valid = {"RISK_ON", "NEUTRAL", "RISK_OFF"}
        assert set(result["ensemble_state"].unique()).issubset(valid)

    def test_score_bounded(self, returns):
        er = EnsembleRegime(seed=42)
        result = er.fit_predict(returns)
        assert result["ensemble_score"].max() <= 1.0 + 1e-6
        assert result["ensemble_score"].min() >= 0.0 - 1e-6


# ── T2.3: Event-Driven Backtester ─────────────────────────────────────

class TestEventBacktester:
    def test_runs_without_error(self, prices):
        def signal_fn(positions, prices_so_far, ts):
            if len(prices_so_far) == 50:  # Buy on day 50
                return [Order("A", 100, OrderType.MARKET)]
            return []

        bt = EventBacktester(prices, signal_fn, latency=1)
        result = bt.run()
        assert "equity_curve" in result
        assert "fills" in result
        assert "returns" in result

    def test_fills_with_latency(self, prices):
        def signal_fn(positions, prices_so_far, ts):
            if len(prices_so_far) == 10:
                return [Order("A", 100)]
            return []

        bt = EventBacktester(prices, signal_fn, latency=2)
        result = bt.run()
        assert result["n_fills"] >= 1

    def test_limit_order_no_fill(self, prices):
        def signal_fn(positions, prices_so_far, ts):
            if len(prices_so_far) == 10:
                return [Order("A", 100, OrderType.LIMIT, limit_price=0.01)]
            return []

        bt = EventBacktester(prices, signal_fn, latency=1)
        result = bt.run()
        assert result["n_fills"] == 0


# ── T2.5: Paper Trading ──────────────────────────────────────────────

class TestPaperBroker:
    def test_order_execution(self):
        broker = PaperBroker()
        broker.submit_order("AAPL", 100, 150.0)
        assert "AAPL" in broker.positions
        assert broker.positions["AAPL"].quantity == 100

    def test_pnl_attribution(self):
        broker = PaperBroker(initial_cash=100_000)
        broker.submit_order("AAPL", 100, 100.0)
        broker.update_prices({"AAPL": 110.0})
        pnl = broker.pnl_attribution()
        assert pnl["unrealised_pnl"] > 0

    def test_reconciliation(self):
        broker = PaperBroker()
        broker.submit_order("AAPL", 100, 150.0)
        diffs = broker.reconcile({"AAPL": 100.0})
        assert len(diffs) == 0

    def test_reconciliation_mismatch(self):
        broker = PaperBroker()
        broker.submit_order("AAPL", 100, 150.0)
        diffs = broker.reconcile({"AAPL": 200.0})
        assert len(diffs) == 1


# ── T3.1: ML Alpha ────────────────────────────────────────────────────

class TestFeatureStore:
    def test_compute_features(self, prices):
        store = FeatureStore()
        features = store.compute_features(prices, lookback=10)
        assert len(features) > 0
        assert features.shape[1] > 0

    def test_get_target(self, prices):
        store = FeatureStore()
        target = store.get_target(prices, horizon=5)
        assert len(target) > 0


class TestMLAlphaModel:
    def test_fit_predict(self):
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(200, 5), columns=[f"f{i}" for i in range(5)])
        y = X.sum(axis=1) + np.random.randn(200) * 0.1
        model = MLAlphaModel(n_estimators=10)
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == 200

    def test_feature_importance(self):
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 3), columns=["a", "b", "c"])
        y = X["a"] * 2 + np.random.randn(100) * 0.1
        model = MLAlphaModel(n_estimators=20)
        model.fit(X, y)
        imp = model.feature_importance()
        assert "a" in imp
        assert imp["a"] > imp["b"]  # feature 'a' should dominate

    def test_cross_validate(self):
        np.random.seed(42)
        X = np.random.randn(200, 4)
        y = X[:, 0] + np.random.randn(200) * 0.5
        model = MLAlphaModel(n_estimators=10)
        cv = model.cross_validate(X, y, n_splits=3, purge_gap=5)
        assert "mean_mse" in cv
        assert cv["n_splits"] > 0


class TestPurgedKFold:
    def test_no_overlap(self):
        X = np.arange(100).reshape(-1, 1)
        cv = PurgedKFold(n_splits=3, purge_gap=5)
        for train_idx, test_idx in cv.split(X):
            assert len(set(train_idx) & set(test_idx)) == 0
            assert max(train_idx) + 5 <= min(test_idx)  # purge gap


# ── T3.2: Multi-Strategy ──────────────────────────────────────────────

class TestMultiStrategy:
    def test_run_all(self, prices):
        mgr = MultiStrategyManager({
            "mom": MomentumStrategy(lookback=10),
            "mr": MeanReversionStrategy(lookback=10),
        })
        signals = mgr.run_all(prices)
        assert "mom" in signals
        assert "mr" in signals

    def test_combine_signals(self, prices):
        mgr = MultiStrategyManager({
            "mom": MomentumStrategy(lookback=10),
            "mr": MeanReversionStrategy(lookback=10),
        })
        signals = mgr.run_all(prices)
        combined = mgr.combine_signals(signals)
        assert combined is not None

    def test_kill_switch(self):
        mgr = MultiStrategyManager(
            {"S1": MomentumStrategy()},
            kill_threshold=-0.05,
        )
        # Simulate bad returns
        for _ in range(30):
            mgr.update_returns({"S1": -0.01})
        assert "S1" in mgr.killed

    def test_status(self, prices):
        mgr = MultiStrategyManager({
            "mom": MomentumStrategy(lookback=10),
        })
        status = mgr.status()
        assert "active" in status
        assert status["strategy_count"] == 1


# ── T3.3: Stress Testing ──────────────────────────────────────────────

class TestStressTester:
    def test_historical_scenario(self):
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)
        result = StressTester.historical_scenario(returns, "2008_crisis")
        assert result["max_drawdown"] < 0
        assert "worst_day" in result

    def test_unknown_scenario_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            StressTester.historical_scenario(np.array([0.01]), "fake_crisis")

    def test_monte_carlo(self):
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)
        result = StressTester.monte_carlo(returns, n_simulations=100, horizon=50)
        assert result["n_simulations"] == 100
        assert result["prob_loss"] >= 0
        assert len(result["sample_paths"]) == 10

    def test_sensitivity_analysis(self):
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)
        results = StressTester.sensitivity_analysis(returns, vol_multipliers=[0.5, 1.0, 2.0])
        assert len(results) == 3
        # Higher vol multiplier → worse max drawdown
        assert results[2]["max_drawdown"] <= results[0]["max_drawdown"]


# ── T3.4: Compliance ──────────────────────────────────────────────────

class TestAuditLog:
    def test_log_and_verify(self):
        log = AuditLog()
        log.log("SIGNAL", {"ticker": "AAPL", "direction": "BUY"})
        log.log("ORDER", {"ticker": "AAPL", "qty": 100})
        assert log.length == 2
        assert log.verify_chain()

    def test_tamper_detected(self):
        log = AuditLog()
        log.log("SIGNAL", {"data": "test"})
        log.log("ORDER", {"data": "test2"})
        # Tamper
        log._entries[0]["data"] = {"data": "tampered"}
        assert not log.verify_chain()

    def test_filter_by_type(self):
        log = AuditLog()
        log.log("SIGNAL", {"a": 1})
        log.log("ORDER", {"b": 2})
        log.log("SIGNAL", {"c": 3})
        signals = log.get_entries(event_type="SIGNAL")
        assert len(signals) == 2


class TestPreTradeCompliance:
    def test_passes(self):
        ptc = PreTradeCompliance()
        result = ptc.check("AAPL", 10, 150.0, total_equity=1_000_000)
        assert result["passed"]

    def test_restricted_ticker(self):
        ptc = PreTradeCompliance(restricted_tickers=["AAPL"])
        result = ptc.check("AAPL", 10, 150.0, total_equity=1_000_000)
        assert not result["passed"]
        assert "Restricted" in result["violations"][0]

    def test_max_order_value(self):
        ptc = PreTradeCompliance(max_order_value=1000)
        result = ptc.check("AAPL", 100, 150.0, total_equity=1_000_000)
        assert not result["passed"]

    def test_concentration_limit(self):
        ptc = PreTradeCompliance(max_position_pct=0.05)
        result = ptc.check("AAPL", 100, 150.0, total_equity=100_000)
        assert not result["passed"]
