"""Tests for ExecutionModel — Phase C validation."""

import pytest

from quantproto.execution_model import ExecutionModel


class TestTransactionCost:
    def test_scales_linearly(self):
        """Double the notional → double the cost."""
        cost1 = ExecutionModel.transaction_cost(100_000, bps=5)
        cost2 = ExecutionModel.transaction_cost(200_000, bps=5)
        assert cost2 == pytest.approx(cost1 * 2)

    def test_known_value(self):
        """100k notional at 5 bps = $50."""
        cost = ExecutionModel.transaction_cost(100_000, bps=5)
        assert cost == pytest.approx(50.0)

    def test_zero_notional(self):
        assert ExecutionModel.transaction_cost(0) == 0.0


class TestSlippage:
    def test_increases_with_order_size(self):
        """Larger orders → more slippage (monotonicity)."""
        adv = 1_000_000
        price = 100.0
        costs = []
        for size in [1000, 5000, 10000, 50000]:
            costs.append(ExecutionModel.slippage(size, adv, price))
        for i in range(len(costs) - 1):
            assert costs[i] < costs[i + 1], "Slippage must increase with order size"

    def test_positive(self):
        slip = ExecutionModel.slippage(1000, 1_000_000, 100.0)
        assert slip > 0

    def test_zero_adv_raises(self):
        with pytest.raises(ValueError, match="ADV must be positive"):
            ExecutionModel.slippage(1000, 0, 100.0)


class TestTotalExecutionCost:
    def test_greater_than_tc_alone(self):
        """Total cost > transaction cost alone (slippage adds)."""
        order_size = 10_000
        price = 50.0
        adv = 1_000_000
        total = ExecutionModel.total_execution_cost(order_size, price, adv)
        tc_only = ExecutionModel.transaction_cost(order_size * price)
        assert total > tc_only

    def test_components_sum(self):
        """Total = tc + slippage."""
        order_size = 5_000
        price = 100.0
        adv = 500_000
        total = ExecutionModel.total_execution_cost(order_size, price, adv)
        tc = ExecutionModel.transaction_cost(order_size * price)
        slip = ExecutionModel.slippage(order_size, adv, price)
        assert total == pytest.approx(tc + slip)

    def test_deterministic(self):
        """Same inputs → same output."""
        a = ExecutionModel.total_execution_cost(1000, 50.0, 1_000_000)
        b = ExecutionModel.total_execution_cost(1000, 50.0, 1_000_000)
        assert a == b
