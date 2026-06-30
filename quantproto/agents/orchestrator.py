"""Orchestrator Agent — chains Alpha → Risk → decision.

Coordinates the alpha and risk agents to produce a final portfolio decision.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quantproto.agents.alpha_agent import AlphaAgent
from quantproto.agents.risk_agent import RiskAgent
from quantproto.agents.integrity_agent import IntegrityAgent
from quantproto.walk_forward import WalkForwardBacktester
from quantproto.regime_model import RegimeHMM

# Minimum engineered-feature rows needed before the HMM regime model is
# considered fittable (below this we leave exposure unscaled rather than
# fabricate a regime from too little data).
_MIN_REGIME_FEATURES = 50

# Per-regime exposure multipliers applied before execution.
_REGIME_SCALE = {"BEAR": 0.3, "NEUTRAL": 0.7, "BULL": 1.0}


class Orchestrator:
    """Chains alpha signal → regime → backtest → risk → integrity → decision.

    Pipeline:
    1. AlphaAgent generates composite signal
    2. RegimeHMM **adjusts exposure per regime** (no lookahead — fit on history
       available at each rebalance) inside the walk-forward signal function
    3. WalkForwardBacktester runs the backtest **net of transaction costs**
    4. RiskAgent evaluates risk + gate
    5. Integrity audit (robustness_report) checks the result for overfitting
    6. Decision: PROCEED only if the risk gate passes **and** the backtest is
       not flagged as likely overfit
    """

    def __init__(
        self,
        lookback: int = 20,
        train_window: int = 60,
        test_window: int = 20,
        seed: int = 42,
        risk_thresholds: dict | None = None,
        cost_bps: float = 5.0,
        regime_aware: bool = True,
    ):
        self.alpha_agent = AlphaAgent(lookback=lookback)
        self.risk_agent = RiskAgent(thresholds=risk_thresholds)
        self.integrity_agent = IntegrityAgent()
        self.train_window = train_window
        self.test_window = test_window
        self.seed = seed
        self.cost_bps = cost_bps
        self.regime_aware = regime_aware

    def _regime_scaled_signal(
        self,
        prices: pd.DataFrame,
        train_prices: pd.DataFrame,
        factor_weights: dict[str, float] | None,
    ) -> pd.DataFrame:
        """Alpha signal for a train window, scaled by the prevailing regime.

        The regime model is fit only on price history available up to the end
        of the training window (``prices`` sliced to that point), so no future
        information leaks into the exposure decision.
        """
        alpha = self.alpha_agent.generate_signal(train_prices, weights=factor_weights)
        signal = pd.DataFrame(alpha["signal"])
        # Re-attach the date index the signal corresponds to (tail of train).
        signal.index = train_prices.index[-len(signal):]

        # Normalise each row to a relative allocation summing to 1, so the
        # regime exposure multiplier maps directly onto invested fraction
        # (scale 0.3 ⇒ 30 % invested, 70 % cash) rather than being normalised
        # away downstream.
        row_sums = signal.abs().sum(axis=1).replace(0.0, np.nan)
        signal = signal.div(row_sums, axis=0).fillna(0.0)

        if not self.regime_aware or len(signal) == 0:
            return signal

        try:
            end_pos = prices.index.get_indexer([train_prices.index[-1]])[0] + 1
            hist_returns = prices.iloc[:end_pos].pct_change().dropna().mean(axis=1)
            features = RegimeHMM.engineer_features(hist_returns, window=self.alpha_agent.lookback)
            if len(features) < _MIN_REGIME_FEATURES:
                return signal
            model = RegimeHMM(seed=self.seed).fit(features)
            states = model.predict_states(features)
            # Scale exposure by regime over the overlapping dates (real use of
            # RegimeHMM.adjust_exposure — previously never called in the pipeline).
            scaled = RegimeHMM.adjust_exposure(
                signal, states,
                bear_scale=_REGIME_SCALE["BEAR"],
                neutral_scale=_REGIME_SCALE["NEUTRAL"],
                bull_scale=_REGIME_SCALE["BULL"],
            )
            if len(scaled) > 0:
                return scaled
        except Exception:
            pass  # graceful degradation — fall back to unscaled alpha
        return signal

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
            "backtest": {returns, equity_curve, n_splits, bootstrap_ci, avg_turnover},
            "risk_report": {...},
            "gate": {passed, violations},
            "regime": {states, confidence} | None,
            "integrity": {score, verdict, ...},
        }
        """
        # Step 1: Generate alpha signal (full-history, for reporting)
        alpha_result = self.alpha_agent.generate_signal(prices, weights=factor_weights)

        # Step 2: Regime detection (reported) — exposure adjustment happens
        # per-window inside the backtest signal function (no lookahead).
        returns = prices.pct_change().dropna()
        mean_returns = returns.mean(axis=1)
        regime_info = None
        try:
            regime = RegimeHMM(seed=self.seed)
            features = regime.engineer_features(mean_returns, window=self.alpha_agent.lookback)
            if len(features) >= _MIN_REGIME_FEATURES:
                regime.fit(features)
                states = regime.predict_states(features)
                confidence = regime.posterior_confidence(features)
                regime_info = {
                    "states": states.tolist(),
                    "confidence": confidence.tolist(),
                }
        except Exception:
            regime_info = None  # Graceful degradation

        # Step 3: Walk-forward backtest — regime-scaled signal, net of costs.
        def signal_fn(train_prices: pd.DataFrame) -> pd.DataFrame:
            return self._regime_scaled_signal(prices, train_prices, factor_weights)

        backtest = WalkForwardBacktester.run(
            prices, signal_fn, self.train_window, self.test_window,
            cost_bps=self.cost_bps,
        )
        bt_returns = backtest["returns"].values

        # Bootstrap CI
        bootstrap_ci = WalkForwardBacktester.bootstrap_sharpe_ci(
            bt_returns, n_boot=500, seed=self.seed,
        )

        # Step 4: Risk evaluation
        portfolio_weights = np.ones(len(prices.columns)) / len(prices.columns)
        risk_result = self.risk_agent.evaluate(
            returns=bt_returns,
            benchmark_returns=mean_returns.iloc[-len(bt_returns):].values,
            weights=portfolio_weights,
        )

        # Step 5: Integrity audit — is this backtest plausibly real or overfit?
        integrity = None
        integrity_gate = None
        if len(bt_returns) >= 2:
            # Average turnover scales the cost-sensitivity sweep; one config
            # was run here, so n_trials = 1 (honest — no factor-weight search).
            integrity_result = self.integrity_agent.evaluate(
                bt_returns,
                n_trials=1,
                turnover=max(backtest.get("avg_turnover", 1.0), 1e-6),
            )
            integrity = integrity_result["report"]
            integrity_gate = integrity_result["gate"]

        # Step 6: Decision — risk gate AND integrity gate both pass.
        risk_ok = risk_result["gate"]["passed"]
        integrity_ok = integrity_gate is None or integrity_gate["passed"]
        action = "PROCEED" if (risk_ok and integrity_ok) else "REJECT"

        return {
            "action": action,
            "signal": alpha_result["signal"],
            "backtest": {
                "returns": backtest["returns"].tolist(),
                "equity_curve": backtest["equity_curve"].tolist(),
                "n_splits": backtest["n_splits"],
                "bootstrap_ci": bootstrap_ci,
                "avg_turnover": backtest.get("avg_turnover", 0.0),
                "cost_bps": self.cost_bps,
            },
            "risk_report": risk_result["risk_report"],
            "gate": risk_result["gate"],
            "integrity_gate": integrity_gate,
            "regime": regime_info,
            "integrity": integrity,
        }
