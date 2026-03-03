"""Feature store — centralised feature computation and caching.

Provides a unified interface for computing, storing, and retrieving
factor features for ML models.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from quantproto.factor_engine import FactorAlphaEngine


class FeatureStore:
    """Centralised feature store for ML models.

    Computes and caches factor-based features for downstream use.
    """

    def __init__(self):
        self.engine = FactorAlphaEngine()
        self._cache: dict[str, pd.DataFrame] = {}
        self._custom_features: dict[str, Callable] = {}

    def register_feature(self, name: str, fn: Callable) -> None:
        """Register a custom feature function.

        fn(prices: DataFrame) -> DataFrame
        """
        self._custom_features[name] = fn

    def compute_features(
        self,
        prices: pd.DataFrame,
        lookback: int = 20,
        include_custom: bool = True,
    ) -> pd.DataFrame:
        """Compute all factor features from price data.

        Returns a DataFrame with multi-level columns: (feature, ticker).
        """
        returns = prices.pct_change().dropna()

        features = {
            "momentum": self.engine.momentum_factor(prices, lookback=lookback),
            "mean_reversion": self.engine.mean_reversion_factor(prices, lookback=lookback),
            "volatility": self.engine.volatility_factor(returns, window=lookback),
            "return_5d": returns.rolling(5).mean(),
            "return_20d": returns.rolling(20).mean(),
            "vol_ratio": (
                returns.rolling(5).std() / returns.rolling(20).std()
            ),
        }

        if include_custom:
            for name, fn in self._custom_features.items():
                try:
                    features[name] = fn(prices)
                except Exception:
                    pass

        # Align all features on common index
        common_index = features["momentum"].index
        for k in features:
            features[k] = features[k].reindex(common_index)

        # Stack into wide DataFrame
        result = pd.concat(features, axis=1)
        return result.dropna()

    def get_target(
        self,
        prices: pd.DataFrame,
        horizon: int = 5,
    ) -> pd.DataFrame:
        """Compute forward return target for ML training."""
        returns = prices.pct_change()
        forward = returns.shift(-horizon).rolling(horizon).mean()
        return forward.dropna()
