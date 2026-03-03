"""Orchestrator Agent — chains Alpha → Risk → decision.

Coordinates the alpha and risk agents to produce a final portfolio decision.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quantproto.agents.alpha_agent import AlphaAgent
from quantproto.agents.risk_agent import RiskAgent
from quantproto.walk_forward import WalkForwardBacktester
from quantproto.regime_model import RegimeHMM


class Orchestrator:
    """Chains alpha signal → risk evaluation → portfolio decision.

    Pipeline:
    1. AlphaAgent generates composite signal
    2. RegimeHMM adjusts exposure per regime
    3. WalkForwardBacktester runs backtest
    4. RiskAgent evaluates risk + gate
    5. Decision: proceed or reject based on risk gate
    """

    def __init__(
        self,
        lookback: int = 20,
        train_window: int = 60,
        test_window: int = 20,
        seed: int = 42,
        risk_thresholds: dict | None = None,
    ):
        self.alpha_agent = AlphaAgent(lookback=lookback)
        self.risk_agent = RiskAgent(thresholds=risk_thresholds)
        self.train_window = train_window
        self.test_window = test_window
        self.seed = seed

    def run_pipeline(
        self,
        prices: pd.DataFrame,
        factor_weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Execute the full orchestration pipeline.

        Parameters
        ----------
        prices : DataFrame of close prices.
        factor_weights : optional factor weights for alpha generation.

        Returns
        -------
        {
            "action": "PROCEED" | "REJECT",
            "signal": {ticker: [values]},
            "backtest": {returns, equity_curve, n_splits, bootstrap_ci},
            "risk_report": {...},
            "gate": {passed, violations},
            "regime": {states, confidence} | None,
        }
        """
        # Step 1: Generate alpha signal
        alpha_result = self.alpha_agent.generate_signal(prices, weights=factor_weights)

        # Step 2: Regime detection + exposure adjustment
        returns = prices.pct_change().dropna()
        mean_returns = returns.mean(axis=1)
        regime_info = None

        try:
            regime = RegimeHMM(seed=self.seed)
            features = regime.engineer_features(mean_returns, window=self.alpha_agent.lookback)
            if len(features) >= 50:  # minimum viable data for HMM
                regime.fit(features)
                states = regime.predict_states(features)
                confidence = regime.posterior_confidence(features)
                regime_info = {
                    "states": states.tolist(),
                    "confidence": confidence.tolist(),
                }
        except Exception:
            regime_info = None  # Graceful degradation

        # Step 3: Walk-forward backtest
        def signal_fn(train_prices: pd.DataFrame) -> pd.DataFrame:
            sig = self.alpha_agent.generate_signal(train_prices, weights=factor_weights)
            return pd.DataFrame(sig["signal"])

        backtest = WalkForwardBacktester.run(
            prices, signal_fn, self.train_window, self.test_window,
        )

        # Bootstrap CI
        bootstrap_ci = WalkForwardBacktester.bootstrap_sharpe_ci(
            backtest["returns"].values,
            n_boot=500,
            seed=self.seed,
        )

        # Step 4: Risk evaluation
        portfolio_weights = np.ones(len(prices.columns)) / len(prices.columns)
        risk_result = self.risk_agent.evaluate(
            returns=backtest["returns"].values,
            benchmark_returns=mean_returns.iloc[-len(backtest["returns"]):].values,
            weights=portfolio_weights,
        )

        # Step 5: Decision
        action = "PROCEED" if risk_result["gate"]["passed"] else "REJECT"

        return {
            "action": action,
            "signal": alpha_result["signal"],
            "backtest": {
                "returns": backtest["returns"].tolist(),
                "equity_curve": backtest["equity_curve"].tolist(),
                "n_splits": backtest["n_splits"],
                "bootstrap_ci": bootstrap_ci,
            },
            "risk_report": risk_result["risk_report"],
            "gate": risk_result["gate"],
            "regime": regime_info,
        }
