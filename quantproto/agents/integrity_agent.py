"""Integrity Agent — audits a backtest for overfitting and gates on it.

Sits alongside AlphaAgent and RiskAgent in the A2A trio. Where the RiskAgent
asks "is this portfolio too risky?", the IntegrityAgent asks the question that
actually sinks most strategies: "is this edge real, or did we overfit it?"

Wraps the integrity engine (Deflated/Probabilistic Sharpe, PBO, cost
sensitivity, red flags → Robustness Score) and turns the verdict into a
go/no-go gate the orchestrator can enforce.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quantproto.integrity.score import robustness_report


class IntegrityAgent:
    """Agent that evaluates the robustness / overfitting risk of a backtest."""

    def __init__(self, min_score: float = 40.0, reject_verdict: str = "likely_overfit"):
        # A backtest fails the integrity gate if it scores below ``min_score``
        # or is explicitly flagged as ``reject_verdict``.
        self.min_score = min_score
        self.reject_verdict = reject_verdict

    def evaluate(
        self,
        returns: np.ndarray | pd.Series,
        n_trials: int = 1,
        turnover: float = 1.0,
        variant_matrix: np.ndarray | None = None,
    ) -> dict[str, Any]:
        """Run the integrity audit and produce a gate decision.

        Returns
        -------
        {
            "report": {... full robustness report ...},
            "gate": {"passed": bool, "score": float, "verdict": str,
                     "reasons": [str]},
        }
        """
        r = np.asarray(returns, dtype=float)
        report = robustness_report(
            r, n_trials=n_trials, turnover=turnover, variant_matrix=variant_matrix,
        )

        reasons: list[str] = []
        if report["verdict"] == self.reject_verdict:
            reasons.append(f"verdict is '{report['verdict']}'")
        if report["score"] < self.min_score:
            reasons.append(f"score {report['score']} < {self.min_score}")
        for flag in report["red_flags"]:
            if flag["severity"] == "high":
                reasons.append(f"red flag: {flag['code']}")

        passed = (
            report["verdict"] != self.reject_verdict
            and report["score"] >= self.min_score
        )

        return {
            "report": report,
            "gate": {
                "passed": passed,
                "score": report["score"],
                "verdict": report["verdict"],
                "reasons": reasons,
            },
        }
