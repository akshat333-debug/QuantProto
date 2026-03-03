"""Tests for Strategy Catalogue (T1.3)."""

import numpy as np
import pandas as pd
import pytest

from quantproto.strategy.base import (
    MomentumStrategy,
    MeanReversionStrategy,
    CompositeStrategy,
)
from quantproto.strategy import registry


@pytest.fixture
def prices():
    np.random.seed(42)
    dates = pd.bdate_range("2023-01-01", periods=100)
    data = {}
    for t in ["A", "B", "C"]:
        data[t] = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.02, 100)))
    return pd.DataFrame(data, index=dates)


class TestMomentumStrategy:
    def test_signal_shape(self, prices):
        strat = MomentumStrategy(lookback=10)
        signal = strat.generate_signal(prices)
        assert signal.shape[1] == prices.shape[1]

    def test_weights_sum_to_one(self, prices):
        strat = MomentumStrategy(lookback=10)
        signal = strat.generate_signal(prices)
        row_sums = signal.sum(axis=1).dropna()
        valid = row_sums[row_sums > 0]
        np.testing.assert_allclose(valid.values, 1.0, atol=1e-6)

    def test_metadata(self):
        strat = MomentumStrategy(lookback=15)
        meta = strat.get_metadata()
        assert meta["name"] == "MomentumStrategy"
        assert meta["lookback"] == 15

    def test_name_property(self):
        strat = MomentumStrategy()
        assert strat.name == "MomentumStrategy"


class TestMeanReversionStrategy:
    def test_signal_shape(self, prices):
        strat = MeanReversionStrategy(lookback=10)
        signal = strat.generate_signal(prices)
        assert signal.shape[1] == prices.shape[1]

    def test_non_negative_weights(self, prices):
        strat = MeanReversionStrategy(lookback=10)
        signal = strat.generate_signal(prices)
        assert (signal >= -1e-10).all().all()


class TestCompositeStrategy:
    def test_signal_shape(self, prices):
        strat = CompositeStrategy(lookback=10)
        signal = strat.generate_signal(prices)
        assert signal.shape[1] == prices.shape[1]

    def test_custom_weights(self, prices):
        weights = {"momentum": 0.7, "mean_reversion": 0.2, "volatility": 0.1}
        strat = CompositeStrategy(lookback=10, factor_weights=weights)
        signal = strat.generate_signal(prices)
        assert signal.shape[1] == prices.shape[1]


class TestRegistry:
    def test_list_strategies(self):
        strategies = registry.list_strategies()
        assert "momentum" in strategies
        assert "mean_reversion" in strategies
        assert "composite" in strategies

    def test_get_strategy(self):
        strat = registry.get("momentum", lookback=15)
        assert isinstance(strat, MomentumStrategy)
        assert strat.lookback == 15

    def test_unknown_strategy_raises(self):
        with pytest.raises(KeyError, match="not registered"):
            registry.get("nonexistent")

    def test_register_custom(self):
        class CustomStrategy(MomentumStrategy):
            pass

        registry.register("custom", CustomStrategy)
        strat = registry.get("custom")
        assert isinstance(strat, CustomStrategy)
