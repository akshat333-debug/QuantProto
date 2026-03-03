"""Abstract strategy base class and built-in strategies.

Every strategy must implement generate_signal() and get_metadata().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd

from quantproto.factor_engine import FactorAlphaEngine
from quantproto.portfolio.optimiser import PortfolioOptimiser


class Strategy(ABC):
    """Abstract base class for all strategies."""

    @abstractmethod
    def generate_signal(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Generate signal/weight DataFrame from price data."""
        ...

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """Return strategy metadata for logging/comparison."""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


# ── Built-in Strategies ──────────────────────────────────────────────

class MomentumStrategy(Strategy):
    """Pure momentum strategy with optional portfolio optimisation."""

    def __init__(self, lookback: int = 20, use_optimiser: str = "equal_weight"):
        self.lookback = lookback
        self.use_optimiser = use_optimiser
        self.engine = FactorAlphaEngine()

    def generate_signal(self, prices: pd.DataFrame) -> pd.DataFrame:
        mom = self.engine.momentum_factor(prices, lookback=self.lookback)
        # Rank and normalise to weights
        ranks = mom.rank(axis=1, pct=True)
        weights = ranks.div(ranks.sum(axis=1), axis=0).fillna(0)

        if self.use_optimiser == "equal_weight":
            return weights

        # Use portfolio optimiser on final period
        returns = prices.pct_change().dropna()
        cov = returns.cov().values
        mu = returns.mean().values

        if self.use_optimiser == "max_sharpe":
            opt_w = PortfolioOptimiser.max_sharpe(mu, cov)
        elif self.use_optimiser == "risk_parity":
            opt_w = PortfolioOptimiser.risk_parity(cov)
        elif self.use_optimiser == "min_vol":
            opt_w = PortfolioOptimiser.min_volatility(cov)
        else:
            opt_w = np.ones(len(mu)) / len(mu)

        # Apply optimised weights as a scaling factor
        opt_series = pd.Series(opt_w, index=weights.columns)
        return weights.mul(opt_series, axis=1).div(
            weights.mul(opt_series, axis=1).sum(axis=1), axis=0
        ).fillna(0)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lookback": self.lookback,
            "optimiser": self.use_optimiser,
        }


class MeanReversionStrategy(Strategy):
    """Mean-reversion z-score strategy."""

    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.engine = FactorAlphaEngine()

    def generate_signal(self, prices: pd.DataFrame) -> pd.DataFrame:
        zscore = self.engine.mean_reversion_factor(prices, lookback=self.lookback)
        # Buy oversold (negative z), sell overbought (positive z)
        signal = -zscore
        ranks = signal.rank(axis=1, pct=True)
        weights = ranks.div(ranks.sum(axis=1), axis=0).fillna(0)
        return weights

    def get_metadata(self) -> dict[str, Any]:
        return {"name": self.name, "lookback": self.lookback}


class CompositeStrategy(Strategy):
    """Multi-factor composite strategy."""

    def __init__(
        self,
        lookback: int = 20,
        factor_weights: dict[str, float] | None = None,
        optimiser: str = "equal_weight",
    ):
        self.lookback = lookback
        self.factor_weights = factor_weights
        self.optimiser = optimiser
        self.engine = FactorAlphaEngine()

    def generate_signal(self, prices: pd.DataFrame) -> pd.DataFrame:
        returns = prices.pct_change().dropna()
        factors = {
            "momentum": self.engine.momentum_factor(prices, lookback=self.lookback),
            "mean_reversion": self.engine.mean_reversion_factor(prices, lookback=self.lookback),
            "volatility": self.engine.volatility_factor(returns, window=self.lookback),
        }
        signal = self.engine.composite_signal(factors, weights=self.factor_weights)
        # Convert to portfolio weights
        weights = signal.div(signal.sum(axis=1), axis=0).fillna(0)
        return weights

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lookback": self.lookback,
            "factor_weights": self.factor_weights,
            "optimiser": self.optimiser,
        }
