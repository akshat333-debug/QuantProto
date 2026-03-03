"""Alpha Agent — generates alpha signals via MCP tools.

Calls factor engine tools and returns a structured signal dict.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quantproto.factor_engine import FactorAlphaEngine


class AlphaAgent:
    """Agent that generates alpha signals from price data.

    This agent wraps the FactorAlphaEngine to produce composite signals
    with metadata about the generation process.
    """

    def __init__(self, lookback: int = 20, window: int = 20):
        self.lookback = lookback
        self.window = window
        self.engine = FactorAlphaEngine()

    def generate_signal(
        self,
        prices: pd.DataFrame,
        weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Generate composite alpha signal.

        Parameters
        ----------
        prices : DataFrame of close prices (index=dates, cols=tickers).
        weights : optional factor weights.

        Returns
        -------
        {
            "signal": {ticker: [values]},
            "metadata": {
                "n_assets": int,
                "n_periods": int,
                "factors_used": [str],
                "lookback": int,
            }
        }
        """
        returns = prices.pct_change().dropna()

        factors = {
            "momentum": self.engine.momentum_factor(prices, lookback=self.lookback),
            "mean_reversion": self.engine.mean_reversion_factor(
                prices, lookback=self.lookback
            ),
            "volatility": self.engine.volatility_factor(returns, window=self.window),
        }

        signal = self.engine.composite_signal(factors, weights=weights)

        return {
            "signal": {col: signal[col].tolist() for col in signal.columns},
            "metadata": {
                "n_assets": len(signal.columns),
                "n_periods": len(signal),
                "factors_used": list(factors.keys()),
                "lookback": self.lookback,
            },
        }
