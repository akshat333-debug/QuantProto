"""Multi-timeframe signal generation.

Provides timeframe resampling and cross-timeframe signal combination.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantproto.factor_engine import FactorAlphaEngine


class MultiTimeframe:
    """Generate and combine signals across multiple timeframes."""

    RESAMPLE_MAP = {
        "weekly": "W",
        "monthly": "ME",
        "quarterly": "QE",
    }

    def __init__(self):
        self.engine = FactorAlphaEngine()

    def resample_prices(
        self, prices: pd.DataFrame, timeframe: str = "weekly"
    ) -> pd.DataFrame:
        """Resample daily prices to lower frequency (OHLC-like close)."""
        rule = self.RESAMPLE_MAP.get(timeframe, timeframe)
        return prices.resample(rule).last().dropna()

    def multi_tf_momentum(
        self,
        prices: pd.DataFrame,
        timeframes: dict[str, int] | None = None,
        weights: dict[str, float] | None = None,
    ) -> pd.DataFrame:
        """Compute momentum across multiple timeframes and combine.

        Parameters
        ----------
        prices : daily price DataFrame.
        timeframes : {timeframe_name: lookback} e.g. {"daily": 20, "weekly": 12}
        weights : {timeframe_name: weight} for combining.

        Returns
        -------
        Combined multi-timeframe momentum signal.
        """
        if timeframes is None:
            timeframes = {"daily": 20, "weekly": 12, "monthly": 6}
        if weights is None:
            weights = {k: 1.0 / len(timeframes) for k in timeframes}

        signals = {}
        for tf_name, lookback in timeframes.items():
            if tf_name == "daily":
                tf_prices = prices
            else:
                tf_prices = self.resample_prices(prices, tf_name)

            mom = self.engine.momentum_factor(tf_prices, lookback=lookback)
            # Rank cross-sectionally
            ranked = mom.rank(axis=1, pct=True)

            if tf_name != "daily":
                # Forward-fill to daily frequency
                ranked = ranked.reindex(prices.index, method="ffill")

            signals[tf_name] = ranked

        # Combine with weights
        common_index = prices.index
        for k in signals:
            signals[k] = signals[k].reindex(common_index)

        combined = sum(weights[k] * signals[k].fillna(0.5) for k in signals)
        return combined

    def adaptive_lookback(
        self,
        prices: pd.DataFrame,
        lookback_range: tuple[int, int] = (10, 60),
        step: int = 5,
    ) -> dict[str, int]:
        """Select optimal lookback per asset by maximising information ratio.

        Tests different lookbacks and picks the one with highest
        signal-to-noise ratio for each asset.
        """
        returns = prices.pct_change().dropna()
        best_lookbacks = {}

        for col in prices.columns:
            best_ir = -np.inf
            best_lb = lookback_range[0]

            for lb in range(lookback_range[0], lookback_range[1] + 1, step):
                mom = self.engine.momentum_factor(
                    prices[[col]], lookback=lb
                ).dropna()
                if len(mom) < lb + 20:
                    continue
                fwd_ret = returns[col].shift(-1).reindex(mom.index).dropna()
                common = mom[col].reindex(fwd_ret.index).dropna()
                fwd_ret = fwd_ret.reindex(common.index)

                if len(common) < 20:
                    continue

                corr = common.corr(fwd_ret)
                ir = corr / (1 - corr**2 + 1e-8)**0.5 * len(common)**0.5
                if ir > best_ir:
                    best_ir = ir
                    best_lb = lb

            best_lookbacks[col] = best_lb

        return best_lookbacks
