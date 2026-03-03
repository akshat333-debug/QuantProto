"""Risk Agent — evaluates risk metrics and gates portfolio decisions.

Calls risk engine tools and returns a structured risk report.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quantproto.risk_engine import RiskEngine


class RiskAgent:
    """Agent that evaluates portfolio risk.

    Computes a full risk report and runs the risk gate against
    configurable thresholds.
    """

    DEFAULT_THRESHOLDS = {
        "var": {"min": -0.05},
        "sharpe": {"min": 0.3},
        "concentration": {"max": 0.5},
    }

    def __init__(self, thresholds: dict | None = None):
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS
        self.engine = RiskEngine()

    def evaluate(
        self,
        returns: np.ndarray | pd.Series,
        benchmark_returns: np.ndarray | pd.Series | None = None,
        weights: np.ndarray | None = None,
    ) -> dict[str, Any]:
        """Generate full risk report.

        Parameters
        ----------
        returns : portfolio return series.
        benchmark_returns : optional benchmark for beta.
        weights : optional portfolio weights for concentration.

        Returns
        -------
        {
            "risk_report": {
                "var_95": float,
                "cvar_95": float,
                "sharpe": float,
                "sortino": float,
                "beta": float | None,
                "concentration": float | None,
            },
            "gate": {"passed": bool, "violations": [...]},
        }
        """
        r = np.asarray(returns)

        report = {
            "var_95": self.engine.value_at_risk(r, confidence=0.95),
            "cvar_95": self.engine.cvar(r, confidence=0.95),
            "sharpe": self.engine.sharpe_ratio(r),
            "sortino": self.engine.sortino_ratio(r),
            "beta": None,
            "concentration": None,
        }

        if benchmark_returns is not None:
            report["beta"] = self.engine.beta(r, np.asarray(benchmark_returns))

        if weights is not None:
            report["concentration"] = self.engine.concentration_risk(weights)

        # Build gate metrics (only those with thresholds)
        gate_metrics = {}
        if "var" in self.thresholds:
            gate_metrics["var"] = report["var_95"]
        if "sharpe" in self.thresholds:
            gate_metrics["sharpe"] = report["sharpe"]
        if "concentration" in self.thresholds and report["concentration"] is not None:
            gate_metrics["concentration"] = report["concentration"]

        gate = self.engine.risk_gate(gate_metrics, self.thresholds)

        return {
            "risk_report": report,
            "gate": gate,
        }
