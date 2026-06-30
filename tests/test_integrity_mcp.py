"""Contract tests for the integrity MCP tools and IntegrityAgent."""

import numpy as np
import pytest

from quantproto.mcp.server import (
    probabilistic_sharpe,
    deflated_sharpe,
    prob_backtest_overfit,
    cost_sensitivity,
    robustness_audit,
    rate_limiter,
)
from quantproto.agents.integrity_agent import IntegrityAgent


def _fn(tool):
    # FastMCP wraps callables; unwrap to the underlying function if needed.
    return getattr(tool, "fn", tool)


@pytest.fixture(autouse=True)
def _reset_limiter():
    rate_limiter.reset()
    yield


class TestIntegrityMCPTools:
    def test_probabilistic_sharpe(self):
        r = list(np.random.RandomState(0).normal(0.001, 0.01, 300))
        out = _fn(probabilistic_sharpe)(r)
        assert 0.0 <= out["psr"] <= 1.0

    def test_deflated_sharpe(self):
        r = list(np.random.RandomState(1).normal(0.001, 0.01, 300))
        out = _fn(deflated_sharpe)(r, n_trials=20, var_sharpe=0.02)
        assert "dsr" in out and 0.0 <= out["dsr"] <= 1.0

    def test_prob_backtest_overfit(self):
        m = np.random.RandomState(2).normal(0, 0.01, size=(320, 8)).tolist()
        out = _fn(prob_backtest_overfit)(m, n_splits=8)
        assert 0.0 <= out["pbo"] <= 1.0
        assert "logits" not in out  # trimmed from the tool response

    def test_cost_sensitivity(self):
        r = list(np.random.RandomState(3).normal(0.001, 0.01, 300))
        out = _fn(cost_sensitivity)(r, turnover=0.5)
        assert "breakeven_bps" in out and "net_sharpe" in out

    def test_robustness_audit(self):
        r = list(np.random.RandomState(4).normal(0.0008, 0.01, 600))
        out = _fn(robustness_audit)(r, turnover=0.3)
        assert 0.0 <= out["score"] <= 100.0
        assert out["verdict"] in {"robust", "fragile", "likely_overfit"}

    def test_robustness_audit_with_variants(self):
        vm = np.random.RandomState(5).normal(0, 0.01, size=(400, 10)).tolist()
        out = _fn(robustness_audit)(list(np.array(vm)[:, 0]), variant_matrix=vm)
        assert out["pbo"] is not None


class TestIntegrityAgent:
    def test_gate_rejects_overfit(self):
        # Short sample + a wide search over pure-noise variants is the textbook
        # overfit: high PBO, short-sample red flag, weak sample adequacy.
        rng = np.random.RandomState(3)
        vm = rng.normal(0, 0.01, size=(90, 80))
        best = vm[:, int(np.argmax(vm.mean(0) / vm.std(0)))]
        res = IntegrityAgent().evaluate(best, variant_matrix=vm, turnover=3.0)
        assert res["gate"]["passed"] is False
        assert res["gate"]["reasons"]

    def test_gate_passes_genuine(self):
        r = np.random.RandomState(7).normal(0.0013, 0.009, 1200)
        res = IntegrityAgent().evaluate(r, n_trials=1, turnover=0.2)
        assert res["gate"]["passed"] is True
