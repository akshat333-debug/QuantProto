"""Advanced regime models — ensemble regime detection.

Combines HMM with volatility regime and correlation regime
for more robust state identification.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quantproto.regime_model import RegimeHMM
from quantproto.analytics.correlation import CorrelationEngine


class EnsembleRegime:
    """Ensemble regime detector combining multiple regime signals.

    Combines:
    1. HMM-based regime (return dynamics)
    2. Volatility regime (realized vol vs threshold)
    3. Correlation regime (cross-asset correlation level)
    """

    VOL_STATES = {"LOW_VOL": 0, "NORMAL_VOL": 1, "HIGH_VOL": 2}
    COMBINED = {"RISK_ON": 1.0, "NEUTRAL": 0.5, "RISK_OFF": 0.25}

    def __init__(
        self,
        hmm_weight: float = 0.4,
        vol_weight: float = 0.3,
        corr_weight: float = 0.3,
        vol_window: int = 20,
        corr_window: int = 60,
        seed: int = 42,
    ):
        self.hmm_weight = hmm_weight
        self.vol_weight = vol_weight
        self.corr_weight = corr_weight
        self.vol_window = vol_window
        self.corr_window = corr_window
        self.seed = seed
        self.hmm = RegimeHMM(seed=seed)

    def fit_predict(
        self, returns: pd.DataFrame
    ) -> dict[str, Any]:
        """Fit all regime models and produce ensemble prediction.

        Parameters
        ----------
        returns : DataFrame of asset returns (multi-column).

        Returns
        -------
        {
            "ensemble_state": Series of state labels,
            "ensemble_score": Series of float scores (0=risk-off, 1=risk-on),
            "hmm_states": Series,
            "vol_regime": Series,
            "corr_regime": Series,
        }
        """
        mean_returns = returns.mean(axis=1)

        # 1. HMM regime
        features = self.hmm.engineer_features(mean_returns, window=self.vol_window)
        self.hmm.fit(features)
        hmm_states = self.hmm.predict_states(features)

        # Map HMM states to scores
        hmm_scores = hmm_states.map({"BULL": 1.0, "NEUTRAL": 0.5, "BEAR": 0.0})

        # 2. Volatility regime
        rolling_vol = mean_returns.rolling(self.vol_window).std() * np.sqrt(252)
        vol_median = rolling_vol.median()
        vol_75 = rolling_vol.quantile(0.75)

        vol_regime = pd.Series("NORMAL_VOL", index=rolling_vol.index)
        vol_regime[rolling_vol < vol_median] = "LOW_VOL"
        vol_regime[rolling_vol > vol_75] = "HIGH_VOL"
        vol_regime = vol_regime.reindex(features.index)

        vol_scores = vol_regime.map({"LOW_VOL": 1.0, "NORMAL_VOL": 0.5, "HIGH_VOL": 0.0})

        # 3. Correlation regime
        if returns.shape[1] >= 2:
            corr_regime = CorrelationEngine.correlation_regime(
                returns, window=min(self.corr_window, len(returns) // 3)
            )
            corr_regime = corr_regime.reindex(features.index, fill_value="NEUTRAL")
            corr_scores = corr_regime.map({"RISK_ON": 1.0, "NEUTRAL": 0.5, "RISK_OFF": 0.0})
        else:
            corr_regime = pd.Series("NEUTRAL", index=features.index)
            corr_scores = pd.Series(0.5, index=features.index)

        # Ensemble score
        ensemble_score = (
            self.hmm_weight * hmm_scores.fillna(0.5)
            + self.vol_weight * vol_scores.fillna(0.5)
            + self.corr_weight * corr_scores.fillna(0.5)
        )

        # Map score to label
        ensemble_state = pd.Series("NEUTRAL", index=ensemble_score.index)
        ensemble_state[ensemble_score > 0.65] = "RISK_ON"
        ensemble_state[ensemble_score < 0.35] = "RISK_OFF"

        return {
            "ensemble_state": ensemble_state,
            "ensemble_score": ensemble_score,
            "hmm_states": hmm_states,
            "vol_regime": vol_regime,
            "corr_regime": corr_regime,
        }

    def adjust_exposure(
        self, signal: pd.Series | pd.DataFrame, ensemble_score: pd.Series
    ) -> pd.Series | pd.DataFrame:
        """Scale signal by ensemble regime score."""
        common = signal.index.intersection(ensemble_score.index)
        return signal.loc[common].mul(ensemble_score.loc[common], axis=0)
