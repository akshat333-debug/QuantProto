"""Factor-based alpha signal generation engine.

All methods are deterministic given the same input data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class FactorAlphaEngine:
    """Generates alpha signals from price and return data.

    All factors return pd.DataFrame (multi-asset) or pd.Series (single-asset)
    aligned with the input index.
    """

    # ------------------------------------------------------------------
    # Individual Factors
    # ------------------------------------------------------------------

    @staticmethod
    def momentum_factor(
        prices: pd.DataFrame | pd.Series,
        lookback: int = 20,
    ) -> pd.DataFrame | pd.Series:
        """Rate-of-change momentum.

        Parameters
        ----------
        prices : DataFrame or Series of closing prices.
        lookback : number of periods for ROC calculation.

        Returns
        -------
        Same shape as *prices*; first *lookback* rows are NaN.
        """
        return prices.pct_change(periods=lookback)

    @staticmethod
    def mean_reversion_factor(
        prices: pd.DataFrame | pd.Series,
        lookback: int = 20,
    ) -> pd.DataFrame | pd.Series:
        """Z-score of price vs. rolling mean (mean-reversion signal).

        A large positive z-score implies price is above its moving average
        (potential short), and vice versa.

        Parameters
        ----------
        prices : DataFrame or Series of closing prices.
        lookback : rolling window size.

        Returns
        -------
        Same shape as *prices*; first *lookback-1* rows are NaN.
        """
        rolling_mean = prices.rolling(window=lookback).mean()
        rolling_std = prices.rolling(window=lookback).std()
        return (prices - rolling_mean) / rolling_std

    @staticmethod
    def volatility_factor(
        returns: pd.DataFrame | pd.Series,
        window: int = 20,
    ) -> pd.DataFrame | pd.Series:
        """Rolling realized volatility.

        Parameters
        ----------
        returns : daily return series or DataFrame.
        window : rolling window for standard deviation.

        Returns
        -------
        Same shape as *returns*; first *window-1* rows are NaN.
        """
        return returns.rolling(window=window).std()

    # ------------------------------------------------------------------
    # Composite Signal
    # ------------------------------------------------------------------

    @staticmethod
    def composite_signal(
        factors: dict[str, pd.DataFrame],
        weights: dict[str, float] | None = None,
    ) -> pd.DataFrame:
        """Combine multiple factors into a single composite signal.

        Steps
        -----
        1. For each factor, percentile-rank across assets (cross-sectional).
        2. Compute weighted average of ranks.
        3. Confidence = mean_rank × (1 − rank_dispersion), where
           rank_dispersion = std of ranks across factors / 0.5.

        Parameters
        ----------
        factors : dict mapping factor name → DataFrame (index=dates, cols=tickers).
        weights : optional dict of factor weights (must match keys). Equal if None.

        Returns
        -------
        DataFrame with columns = tickers, values in [0, 1].
        """
        if weights is None:
            weights = {k: 1.0 / len(factors) for k in factors}

        # Normalise weights
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        # Align all factors on common index (they may differ in length)
        common_index = factors[list(factors.keys())[0]].index
        for df in factors.values():
            common_index = common_index.intersection(df.index)

        aligned: dict[str, pd.DataFrame] = {}
        for name, df in factors.items():
            aligned[name] = df.loc[common_index]

        # Cross-sectional percentile rank each factor
        ranked: dict[str, pd.DataFrame] = {}
        for name, df in aligned.items():
            ranked[name] = df.rank(axis=1, pct=True)

        first_ranked = list(ranked.values())[0]

        # Weighted average of ranks
        combined = pd.DataFrame(
            np.zeros_like(first_ranked.values),
            index=first_ranked.index,
            columns=first_ranked.columns,
        )
        for name, rdf in ranked.items():
            combined += weights[name] * rdf

        # Rank dispersion → confidence adjustment
        rank_stack = np.stack([rdf.values for rdf in ranked.values()], axis=0)  # (F, T, A)
        dispersion = np.std(rank_stack, axis=0) / 0.5  # normalised by max possible std
        dispersion = np.clip(dispersion, 0, 1)

        confidence = combined.values * (1.0 - dispersion)
        confidence = np.clip(confidence, 0, 1)

        result = pd.DataFrame(confidence, index=combined.index, columns=combined.columns)

        # Replace any NaN with 0 (from warmup period)
        result = result.fillna(0.0)

        return result
