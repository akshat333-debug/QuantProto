"""Stress testing and scenario analysis.

Historical replay, Monte Carlo simulation, and sensitivity analysis.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quantproto.analytics import DrawdownAnalytics
from quantproto.risk_engine import RiskEngine


class StressTester:
    """Portfolio stress testing engine."""

    # Historical crisis periods (approximate trading days)
    SCENARIOS = {
        "2008_crisis": {"vol_multiplier": 3.0, "drift_shift": -0.003, "duration": 252},
        "covid_crash": {"vol_multiplier": 4.0, "drift_shift": -0.005, "duration": 30},
        "dotcom_bust": {"vol_multiplier": 2.0, "drift_shift": -0.002, "duration": 504},
        "flash_crash": {"vol_multiplier": 8.0, "drift_shift": -0.01, "duration": 5},
        "rate_hike": {"vol_multiplier": 1.5, "drift_shift": -0.001, "duration": 126},
    }

    @staticmethod
    def historical_scenario(
        returns: np.ndarray,
        scenario_name: str,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Simulate a historical stress scenario.

        Modifies return distribution to match crisis characteristics.
        """
        params = StressTester.SCENARIOS.get(scenario_name)
        if params is None:
            raise ValueError(f"Unknown scenario: {scenario_name}. Available: {list(StressTester.SCENARIOS.keys())}")

        rng = np.random.RandomState(seed)
        n = params["duration"]
        base_vol = np.std(returns)
        base_mean = np.mean(returns)

        stressed = rng.normal(
            base_mean + params["drift_shift"],
            base_vol * params["vol_multiplier"],
            n,
        )

        equity = np.cumprod(1 + stressed)

        return {
            "scenario": scenario_name,
            "stressed_returns": stressed,
            "equity_curve": equity,
            "max_drawdown": DrawdownAnalytics.max_drawdown(equity),
            "total_return": float(equity[-1] / equity[0] - 1),
            "worst_day": float(np.min(stressed)),
            "var_95": float(RiskEngine.value_at_risk(stressed, 0.95)),
        }

    @staticmethod
    def monte_carlo(
        returns: np.ndarray,
        n_simulations: int = 1000,
        horizon: int = 252,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Monte Carlo forward simulation.

        Generates random paths from fitted return distribution.
        """
        rng = np.random.RandomState(seed)
        mu = np.mean(returns)
        sigma = np.std(returns)

        terminal_values = []
        max_drawdowns = []
        paths = []

        for _ in range(n_simulations):
            sim_returns = rng.normal(mu, sigma, horizon)
            equity = np.cumprod(1 + sim_returns)
            terminal_values.append(equity[-1])
            max_drawdowns.append(DrawdownAnalytics.max_drawdown(equity))
            if len(paths) < 10:  # Store first 10 paths for plotting
                paths.append(equity.tolist())

        return {
            "n_simulations": n_simulations,
            "horizon": horizon,
            "median_terminal": float(np.median(terminal_values)),
            "percentile_5": float(np.percentile(terminal_values, 5)),
            "percentile_95": float(np.percentile(terminal_values, 95)),
            "prob_loss": float(np.mean([t < 1.0 for t in terminal_values])),
            "median_max_dd": float(np.median(max_drawdowns)),
            "worst_max_dd": float(np.min(max_drawdowns)),
            "sample_paths": paths,
        }

    @staticmethod
    def sensitivity_analysis(
        returns: np.ndarray,
        vol_multipliers: list[float] | None = None,
        seed: int = 42,
    ) -> list[dict[str, Any]]:
        """Sensitivity analysis — how metrics change with volatility.

        Tests portfolio at different volatility levels.
        """
        if vol_multipliers is None:
            vol_multipliers = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]

        rng = np.random.RandomState(seed)
        mu = np.mean(returns)
        sigma = np.std(returns)
        results = []

        for mult in vol_multipliers:
            stressed = rng.normal(mu, sigma * mult, len(returns))
            equity = np.cumprod(1 + stressed)

            results.append({
                "vol_multiplier": mult,
                "annualised_vol": float(np.std(stressed) * np.sqrt(252)),
                "sharpe": float(RiskEngine.sharpe_ratio(stressed)),
                "max_drawdown": float(DrawdownAnalytics.max_drawdown(equity)),
                "var_95": float(RiskEngine.value_at_risk(stressed, 0.95)),
                "total_return": float(equity[-1] - 1),
            })

        return results
