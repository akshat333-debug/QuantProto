"""ML alpha models with purged cross-validation.

Provides LightGBM/sklearn-based factor models with time-series-safe
validation and feature importance via permutation.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error


class PurgedKFold:
    """Purged walk-forward K-fold for time series data.

    Ensures no leakage between train and test by purging
    observations near the boundary.

    Parameters
    ----------
    n_splits : number of folds.
    purge_gap : number of rows to skip between train and test.
    """

    def __init__(self, n_splits: int = 5, purge_gap: int = 5):
        self.n_splits = n_splits
        self.purge_gap = purge_gap

    def split(self, X: np.ndarray | pd.DataFrame):
        n = len(X)
        fold_size = n // (self.n_splits + 1)

        for i in range(self.n_splits):
            train_end = fold_size * (i + 1)
            test_start = train_end + self.purge_gap
            test_end = min(test_start + fold_size, n)

            if test_start >= n or test_end <= test_start:
                continue

            train_idx = np.arange(0, train_end)
            test_idx = np.arange(test_start, test_end)
            yield train_idx, test_idx


class MLAlphaModel:
    """Gradient boosting alpha model with purged CV.

    Uses sklearn's GradientBoostingRegressor as a baseline
    (avoids hard dependency on LightGBM).
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 3,
        learning_rate: float = 0.1,
        seed: int = 42,
    ):
        self.model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=seed,
        )
        self.feature_names: list[str] = []
        self.is_fitted = False

    def fit(self, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray) -> "MLAlphaModel":
        """Fit the model."""
        if isinstance(X, pd.DataFrame):
            self.feature_names = list(X.columns)
        X_arr = np.asarray(X)
        y_arr = np.asarray(y).ravel()

        # Remove NaN rows
        mask = ~(np.isnan(X_arr).any(axis=1) | np.isnan(y_arr))
        self.model.fit(X_arr[mask], y_arr[mask])
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Generate predictions."""
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        return self.model.predict(np.asarray(X))

    def feature_importance(self) -> dict[str, float]:
        """Return feature importances."""
        if not self.is_fitted:
            raise RuntimeError("Model not fitted.")
        importances = self.model.feature_importances_
        names = self.feature_names or [f"f{i}" for i in range(len(importances))]
        return dict(zip(names, importances.tolist()))

    def cross_validate(
        self,
        X: pd.DataFrame | np.ndarray,
        y: pd.Series | np.ndarray,
        n_splits: int = 5,
        purge_gap: int = 5,
    ) -> dict[str, Any]:
        """Purged walk-forward cross-validation.

        Returns
        -------
        {mse_scores, mean_mse, std_mse, n_splits}
        """
        X_arr = np.asarray(X)
        y_arr = np.asarray(y).ravel()

        mask = ~(np.isnan(X_arr).any(axis=1) | np.isnan(y_arr))
        X_clean = X_arr[mask]
        y_clean = y_arr[mask]

        cv = PurgedKFold(n_splits=n_splits, purge_gap=purge_gap)
        scores = []

        for train_idx, test_idx in cv.split(X_clean):
            model = GradientBoostingRegressor(
                n_estimators=self.model.n_estimators,
                max_depth=self.model.max_depth,
                learning_rate=self.model.learning_rate,
                random_state=self.model.random_state,
            )
            model.fit(X_clean[train_idx], y_clean[train_idx])
            preds = model.predict(X_clean[test_idx])
            mse = mean_squared_error(y_clean[test_idx], preds)
            scores.append(mse)

        return {
            "mse_scores": scores,
            "mean_mse": float(np.mean(scores)),
            "std_mse": float(np.std(scores)),
            "n_splits": len(scores),
        }
