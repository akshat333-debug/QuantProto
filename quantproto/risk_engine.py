"""Risk metrics and gating engine.

Provides portfolio-level risk measures: VaR, CVaR, Sharpe, Sortino,
Beta (vs. benchmark), concentration risk (HHI), and a configurable
risk gate that flags threshold violations.

All methods are deterministic and operate on numpy/pandas inputs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class RiskEngine:
    """Compute risk metrics from return series."""

    # ------------------------------------------------------------------
    # Value-at-Risk
    # ------------------------------------------------------------------

    @staticmethod
    def value_at_risk(
        returns: np.ndarray | pd.Series,
        confidence: float = 0.95,
    ) -> float:
        """Historical Value-at-Risk.

        Parameters
        ----------
        returns : array of periodic returns.
        confidence : VaR confidence level (e.g., 0.95 → 5 % tail).

        Returns
        -------
        VaR as a negative number (loss).
        """
        returns = np.asarray(returns)
        return float(np.percentile(returns, (1 - confidence) * 100))

    @staticmethod
    def cvar(
        returns: np.ndarray | pd.Series,
        confidence: float = 0.95,
    ) -> float:
        """Conditional VaR (Expected Shortfall).

        Mean of returns at or below the VaR threshold.
        """
        returns = np.asarray(returns)
        var = np.percentile(returns, (1 - confidence) * 100)
        return float(np.mean(returns[returns <= var]))

    # ------------------------------------------------------------------
    # Risk-adjusted return ratios
    # ------------------------------------------------------------------

    @staticmethod
    def sharpe_ratio(
        returns: np.ndarray | pd.Series,
        rf: float = 0.0,
        periods_per_year: int = 252,
    ) -> float:
        """Annualised Sharpe ratio.

        Parameters
        ----------
        returns : daily (or periodic) return series.
        rf : risk-free rate per period.
        periods_per_year : annualisation factor (252 for daily).
        """
        returns = np.asarray(returns)
        excess = returns - rf
        std = np.std(excess, ddof=1)
        if std < 1e-12:
            return 0.0
        return float(np.mean(excess) / std * np.sqrt(periods_per_year))

    @staticmethod
    def sortino_ratio(
        returns: np.ndarray | pd.Series,
        rf: float = 0.0,
        periods_per_year: int = 252,
    ) -> float:
        """Annualised Sortino ratio (downside deviation only).

        Uses the standard deviation of negative excess returns as
        the denominator.
        """
        returns = np.asarray(returns)
        excess = returns - rf
        downside = excess[excess < 0]
        if len(downside) == 0:
            # No negative returns → infinite risk-adjusted return
            return float('inf') if np.mean(excess) > 0 else 0.0
        dd_std = np.std(downside, ddof=1)
        if dd_std < 1e-12:
            return float('inf') if np.mean(excess) > 0 else 0.0
        return float(np.mean(excess) / dd_std * np.sqrt(periods_per_year))

    # ------------------------------------------------------------------
    # Beta
    # ------------------------------------------------------------------

    @staticmethod
    def beta(
        returns: np.ndarray | pd.Series,
        benchmark_returns: np.ndarray | pd.Series,
    ) -> float:
        """Regression beta against a benchmark.

        beta = cov(r, b) / var(b)
        """
        r = np.asarray(returns)
        b = np.asarray(benchmark_returns)
        cov_matrix = np.cov(r, b)
        var_b = cov_matrix[1, 1]
        if var_b == 0:
            return 0.0
        return float(cov_matrix[0, 1] / var_b)

    # ------------------------------------------------------------------
    # Concentration risk
    # ------------------------------------------------------------------

    @staticmethod
    def concentration_risk(weights: np.ndarray | pd.Series) -> float:
        """Herfindahl–Hirschman Index (HHI).

        HHI = sum(w_i^2). Ranges from 1/n (perfectly diversified)
        to 1.0 (single asset).
        """
        w = np.asarray(weights, dtype=float)
        return float(np.sum(w ** 2))

    # ------------------------------------------------------------------
    # Risk gate
    # ------------------------------------------------------------------

    @staticmethod
    def risk_gate(
        metrics: dict[str, float],
        thresholds: dict[str, dict],
    ) -> dict:
        """Check risk metrics against configurable thresholds.

        Parameters
        ----------
        metrics : dict of metric_name → value (e.g. {"var": -0.03, "sharpe": 1.2}).
        thresholds : dict of metric_name → {"max": ..., "min": ...}.
            - "max": metric must be ≤ this value.
            - "min": metric must be ≥ this value.

        Returns
        -------
        {"passed": bool, "violations": [{"metric": str, "value": float, "rule": str, "limit": float}]}
        """
        violations = []
        for name, value in metrics.items():
            if name not in thresholds:
                continue
            t = thresholds[name]
            if "max" in t and value > t["max"]:
                violations.append(
                    {"metric": name, "value": value, "rule": "max", "limit": t["max"]}
                )
            if "min" in t and value < t["min"]:
                violations.append(
                    {"metric": name, "value": value, "rule": "min", "limit": t["min"]}
                )

        return {"passed": len(violations) == 0, "violations": violations}
