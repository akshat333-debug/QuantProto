"""Hidden Markov Model regime detection.

Uses a Gaussian HMM to classify market regimes (BULL / NEUTRAL / BEAR)
from return-based features. Exposure is scaled per-regime.
All random operations are seeded for determinism.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM


class RegimeHMM:
    """HMM-based regime detector with exposure scaling."""

    LABELS = ["BEAR", "NEUTRAL", "BULL"]

    @staticmethod
    def _labels_for(n_states: int) -> list[str]:
        """Ordered regime labels (lowest mean-return → highest).

        Uses the canonical BEAR/NEUTRAL/BULL names for 2- and 3-state models,
        and generic ``REGIME_i`` labels otherwise so any ``n_states`` works.
        """
        if n_states == 2:
            return ["BEAR", "BULL"]
        if n_states == 3:
            return ["BEAR", "NEUTRAL", "BULL"]
        return [f"REGIME_{i}" for i in range(n_states)]

    def __init__(self, n_states: int = 3, seed: int = 42):
        self.n_states = n_states
        self.seed = seed
        self._model: GaussianHMM | None = None
        self._state_label_map: dict[int, str] | None = None

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    @staticmethod
    def engineer_features(
        returns: pd.Series | pd.DataFrame,
        window: int = 20,
    ) -> pd.DataFrame:
        """Build feature matrix from returns.

        Features:
        - rolling mean return
        - rolling volatility (std)
        - rolling skewness

        Parameters
        ----------
        returns : daily return series (single column preferred).
        window : rolling window size.

        Returns
        -------
        DataFrame with columns [mean, volatility, skewness], NaN rows dropped.
        """
        if isinstance(returns, pd.DataFrame):
            if returns.shape[1] > 1:
                # Use mean across assets for regime detection
                returns = returns.mean(axis=1)
            else:
                returns = returns.iloc[:, 0]

        features = pd.DataFrame(
            {
                "mean": returns.rolling(window).mean(),
                "volatility": returns.rolling(window).std(),
                "skewness": returns.rolling(window).skew(),
            },
            index=returns.index,
        )
        return features.dropna()

    # ------------------------------------------------------------------
    # Model fitting
    # ------------------------------------------------------------------

    def fit(self, features: pd.DataFrame) -> "RegimeHMM":
        """Fit the Gaussian HMM.

        Parameters
        ----------
        features : feature DataFrame from engineer_features.

        Returns
        -------
        self (for chaining).
        """
        X = features.values
        # "full" covariance can degenerate to non-positive-definite during EM
        # (raises ValueError from hmmlearn) — the exact seeds that break vary
        # with numpy/scipy versions. Regularise, then fall back to the
        # better-conditioned "diag" before giving up.
        last_err: Exception | None = None
        for cov_type, min_covar in (("full", 1e-3), ("full", 1e-2), ("diag", 1e-3)):
            model = GaussianHMM(
                n_components=self.n_states,
                covariance_type=cov_type,
                min_covar=min_covar,
                n_iter=100,
                random_state=self.seed,
            )
            try:
                model.fit(X)
                model.predict(X)  # decode can fail even when fit() succeeded
            except ValueError as e:  # non-PSD covariance
                last_err = e
                continue
            self._model = model
            break
        else:
            raise RuntimeError(
                "HMM failed to fit: covariance stayed non-positive-definite "
                "under every fallback. Check for constant or near-duplicate "
                f"feature columns. Underlying error: {last_err}"
            ) from last_err

        # Label states by their mean-return feature (col 0)
        means = self._model.means_[:, 0]
        sorted_indices = np.argsort(means)  # lowest mean → most bearish
        labels = self._labels_for(self.n_states)
        self._state_label_map = {}
        for rank, state_idx in enumerate(sorted_indices):
            self._state_label_map[state_idx] = labels[rank]

        return self

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_states(self, features: pd.DataFrame) -> pd.Series:
        """Predict regime labels.

        Parameters
        ----------
        features : feature DataFrame (same format as fit input).

        Returns
        -------
        Series of regime labels ("BULL", "NEUTRAL", "BEAR").
        """
        if self._model is None:
            raise RuntimeError("Model not fitted. Call .fit() first.")

        raw_states = self._model.predict(features.values)
        labels = pd.Series(
            [self._state_label_map[s] for s in raw_states],
            index=features.index,
            name="regime",
        )
        return labels

    def posterior_confidence(self, features: pd.DataFrame) -> pd.Series:
        """Per-observation confidence (max posterior probability).

        Parameters
        ----------
        features : feature DataFrame.

        Returns
        -------
        Series of confidence values in [1/n_states, 1.0].
        """
        if self._model is None:
            raise RuntimeError("Model not fitted. Call .fit() first.")

        proba = self._model.predict_proba(features.values)
        confidence = pd.Series(
            np.max(proba, axis=1),
            index=features.index,
            name="confidence",
        )
        return confidence

    # ------------------------------------------------------------------
    # Exposure adjustment
    # ------------------------------------------------------------------

    @staticmethod
    def adjust_exposure(
        signal: pd.DataFrame | pd.Series,
        states: pd.Series,
        bear_scale: float = 0.3,
        neutral_scale: float = 0.7,
        bull_scale: float = 1.0,
    ) -> pd.DataFrame | pd.Series:
        """Scale signal by regime.

        Parameters
        ----------
        signal : alpha signal (same index as states).
        states : regime labels from predict_states.
        bear_scale : multiplicative factor for BEAR regime.
        neutral_scale : multiplicative factor for NEUTRAL.
        bull_scale : multiplicative factor for BULL.

        Returns
        -------
        Scaled signal, same shape as input.
        """
        scale_map = {
            "BEAR": bear_scale,
            "NEUTRAL": neutral_scale,
            "BULL": bull_scale,
        }

        # Align on common index
        common_idx = signal.index.intersection(states.index)
        aligned_signal = signal.loc[common_idx]
        aligned_states = states.loc[common_idx]

        scales = aligned_states.map(scale_map)

        if isinstance(aligned_signal, pd.DataFrame):
            return aligned_signal.multiply(scales, axis=0)
        return aligned_signal * scales
