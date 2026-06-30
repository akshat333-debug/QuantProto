"""Tests for transaction-cost sensitivity analysis."""

import numpy as np
import pytest

from quantproto.integrity.cost_sensitivity import cost_sensitivity_sweep


class TestCostSweep:
    def test_output_keys(self):
        r = np.random.RandomState(0).normal(0.001, 0.01, 500)
        out = cost_sensitivity_sweep(r, turnover=0.5)
        for k in ["bps_grid", "net_sharpe", "gross_sharpe", "breakeven_bps"]:
            assert k in out

    def test_net_sharpe_monotonic_decreasing(self):
        r = np.random.RandomState(1).normal(0.001, 0.01, 500)
        out = cost_sensitivity_sweep(r, turnover=1.0)
        ns = out["net_sharpe"]
        assert all(ns[i] >= ns[i + 1] - 1e-9 for i in range(len(ns) - 1))

    def test_zero_cost_equals_gross(self):
        r = np.random.RandomState(2).normal(0.001, 0.01, 500)
        out = cost_sensitivity_sweep(r, turnover=1.0)
        assert out["net_sharpe"][0] == pytest.approx(out["gross_sharpe"], abs=1e-9)

    def test_breakeven_positive_for_profitable(self):
        r = np.random.RandomState(3).normal(0.002, 0.01, 500)
        out = cost_sensitivity_sweep(r, turnover=1.0)
        assert out["breakeven_bps"] > 0

    def test_breakeven_zero_for_unprofitable(self):
        r = np.random.RandomState(4).normal(-0.001, 0.01, 500)
        out = cost_sensitivity_sweep(r, turnover=1.0)
        assert out["breakeven_bps"] == 0.0

    def test_higher_turnover_lower_breakeven(self):
        r = np.random.RandomState(5).normal(0.002, 0.01, 500)
        low = cost_sensitivity_sweep(r, turnover=0.5)["breakeven_bps"]
        high = cost_sensitivity_sweep(r, turnover=2.0)["breakeven_bps"]
        assert high < low
