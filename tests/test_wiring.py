"""Regression tests: the pipeline stays *connected*.

These exist specifically to prevent the original audit finding — components
built and shown but never actually wired into the decision — from returning.
"""

import logging

import numpy as np
import pandas as pd
import pytest

from quantproto.walk_forward import WalkForwardBacktester
from quantproto.agents.orchestrator import Orchestrator
from quantproto.demo.data_loader import generate_prices

logging.getLogger("hmmlearn").setLevel(logging.ERROR)


@pytest.fixture(scope="module")
def prices():
    return generate_prices(["AAA", "BBB", "CCC", "DDD"], n_days=504, seed=7)


class TestCostsWired:
    def test_cost_reduces_returns(self, prices):
        def alt_signal(train):
            # Alternating concentration forces turnover between rebalances.
            n = train.shape[1]
            w = np.zeros(n)
            w[len(train) % n] = 1.0
            return pd.DataFrame(np.tile(w, (len(train), 1)),
                                index=train.index, columns=train.columns)

        free = WalkForwardBacktester.run(prices, alt_signal, 60, 20, cost_bps=0.0)
        costed = WalkForwardBacktester.run(prices, alt_signal, 60, 20, cost_bps=50.0)
        assert costed["total_cost"] > 0
        assert sum(costed["returns"]) < sum(free["returns"])

    def test_turnover_reported(self, prices):
        def ew(train):
            n = train.shape[1]
            return pd.DataFrame(np.ones((len(train), n)) / n,
                                index=train.index, columns=train.columns)

        res = WalkForwardBacktester.run(prices, ew, 60, 20, cost_bps=5.0)
        assert "avg_turnover" in res and res["avg_turnover"] >= 0


class TestOrchestratorWired:
    def test_pipeline_emits_integrity(self, prices):
        out = Orchestrator(train_window=120, test_window=20, seed=7).run_pipeline(prices)
        assert out["integrity"] is not None
        assert "score" in out["integrity"]
        assert out["action"] in {"PROCEED", "REJECT"}

    def test_backtest_reports_costs(self, prices):
        out = Orchestrator(train_window=120, test_window=20, cost_bps=5.0).run_pipeline(prices)
        assert out["backtest"]["cost_bps"] == 5.0
        assert out["backtest"]["avg_turnover"] >= 0

    def test_regime_aware_changes_result(self, prices):
        # Regime scaling must actually move the backtest, proving it is wired
        # in (not merely computed and discarded as before).
        on = Orchestrator(train_window=120, test_window=20, seed=7, regime_aware=True)
        off = Orchestrator(train_window=120, test_window=20, seed=7, regime_aware=False)
        r_on = on.run_pipeline(prices)["backtest"]["equity_curve"]
        r_off = off.run_pipeline(prices)["backtest"]["equity_curve"]
        assert r_on[-1] != r_off[-1]


class TestRiskGateWired:
    """The dashboard risk gate must use correct threshold direction.

    Regression: the API once passed {"var": {"max": -0.05}}, which rejected
    every portfolio whose daily VaR was *better* (less negative) than -5%,
    while waving through portfolios losing more than 5% a day.
    """

    def test_healthy_var_is_not_a_violation(self):
        from fastapi.testclient import TestClient
        from quantproto.dashboard.api import app

        resp = TestClient(app).post(
            "/api/run-analysis",
            json={"tickers": ["AAA", "BBB", "CCC"], "n_days": 300, "seed": 7},
        )
        assert resp.status_code == 200
        summary = resp.json()["summary"]
        var_violations = [
            v for v in summary["gate_violations"] if v["metric"] == "var"
        ]
        if summary["var_95"] / 100 > -0.05:  # VaR safely inside the limit
            assert var_violations == []
        else:  # a genuinely bad VaR must still be caught
            assert var_violations


class TestRegimeHMMRobustFit:
    """RegimeHMM must not crash on non-positive-definite covariance.

    Regression: `covariance_type="full"` degenerates during EM for some seeds
    (8/30 before the fix, and the failing set shifts with numpy/scipy versions
    — it broke CI on 3.11 while passing locally on 3.12). fit() could also
    succeed while the *decode* later raised, so the fallback validates both.
    """

    def test_many_seeds_fit_and_predict(self):
        from quantproto.regime import EnsembleRegime

        rng = np.random.default_rng(42)
        dates = pd.bdate_range("2022-01-03", periods=300)
        prices = pd.DataFrame(
            {t: 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, 300)))
             for t in ("A", "B", "C")},
            index=dates,
        )
        returns = prices.pct_change().dropna()
        for seed in range(25):
            result = EnsembleRegime(seed=seed).fit_predict(returns)
            assert "ensemble_state" in result
