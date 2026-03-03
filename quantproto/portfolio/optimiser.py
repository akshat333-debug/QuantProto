"""Portfolio optimisation engine.

Provides mean-variance, minimum-volatility, maximum-Sharpe, risk-parity,
and Kelly criterion allocation with turnover and weight constraints.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


class PortfolioOptimiser:
    """Multi-objective portfolio optimiser with constraints."""

    # ------------------------------------------------------------------
    # Mean-Variance (Markowitz)
    # ------------------------------------------------------------------

    @staticmethod
    def mean_variance(
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        risk_aversion: float = 1.0,
        weight_bounds: tuple[float, float] = (0.0, 1.0),
        max_weight: float | None = None,
    ) -> np.ndarray:
        """Mean-variance optimisation.

        max: w'μ - (λ/2) w'Σw
        s.t. sum(w) = 1, bounds per asset.
        """
        n = len(expected_returns)
        bounds = [(weight_bounds[0], max_weight or weight_bounds[1])] * n

        def objective(w):
            ret = w @ expected_returns
            risk = w @ cov_matrix @ w
            return -(ret - 0.5 * risk_aversion * risk)

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        x0 = np.ones(n) / n

        result = minimize(objective, x0, method="SLSQP", bounds=bounds,
                         constraints=constraints)
        return result.x

    # ------------------------------------------------------------------
    # Minimum Volatility
    # ------------------------------------------------------------------

    @staticmethod
    def min_volatility(
        cov_matrix: np.ndarray,
        weight_bounds: tuple[float, float] = (0.0, 1.0),
        max_weight: float | None = None,
    ) -> np.ndarray:
        """Minimum volatility portfolio."""
        n = cov_matrix.shape[0]
        bounds = [(weight_bounds[0], max_weight or weight_bounds[1])] * n

        def objective(w):
            return w @ cov_matrix @ w

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        x0 = np.ones(n) / n

        result = minimize(objective, x0, method="SLSQP", bounds=bounds,
                         constraints=constraints)
        return result.x

    # ------------------------------------------------------------------
    # Maximum Sharpe
    # ------------------------------------------------------------------

    @staticmethod
    def max_sharpe(
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        rf: float = 0.0,
        weight_bounds: tuple[float, float] = (0.0, 1.0),
        max_weight: float | None = None,
    ) -> np.ndarray:
        """Maximum Sharpe ratio portfolio."""
        n = len(expected_returns)
        bounds = [(weight_bounds[0], max_weight or weight_bounds[1])] * n

        def neg_sharpe(w):
            ret = w @ expected_returns - rf
            vol = np.sqrt(w @ cov_matrix @ w)
            if vol < 1e-12:
                return 0.0
            return -ret / vol

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        x0 = np.ones(n) / n

        result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds,
                         constraints=constraints)
        return result.x

    # ------------------------------------------------------------------
    # Risk Parity
    # ------------------------------------------------------------------

    @staticmethod
    def risk_parity(
        cov_matrix: np.ndarray,
        risk_budget: np.ndarray | None = None,
    ) -> np.ndarray:
        """Risk-parity allocation (equal risk contribution).

        Each asset contributes equally to portfolio variance.
        """
        n = cov_matrix.shape[0]
        if risk_budget is None:
            risk_budget = np.ones(n) / n

        def objective(w):
            port_var = w @ cov_matrix @ w
            marginal_contrib = cov_matrix @ w
            risk_contrib = w * marginal_contrib
            # Minimise deviation from target risk budget
            target = risk_budget * port_var
            return np.sum((risk_contrib - target) ** 2)

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.01, 1.0)] * n
        x0 = np.ones(n) / n

        result = minimize(objective, x0, method="SLSQP", bounds=bounds,
                         constraints=constraints)
        return result.x

    # ------------------------------------------------------------------
    # Kelly Criterion
    # ------------------------------------------------------------------

    @staticmethod
    def kelly_criterion(
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        fraction: float = 0.5,
    ) -> np.ndarray:
        """Kelly criterion position sizing.

        Full Kelly: w = Σ⁻¹ μ
        Fractional Kelly: w = f × Σ⁻¹ μ  (f < 1 for safety)

        Parameters
        ----------
        fraction : Kelly fraction (0.5 = half-Kelly, commonly used).
        """
        try:
            inv_cov = np.linalg.inv(cov_matrix)
        except np.linalg.LinAlgError:
            inv_cov = np.linalg.pinv(cov_matrix)

        raw_weights = fraction * inv_cov @ expected_returns
        # Normalise to sum to 1, keep direction
        total = np.sum(np.abs(raw_weights))
        if total < 1e-12:
            return np.ones(len(expected_returns)) / len(expected_returns)
        return raw_weights / total

    # ------------------------------------------------------------------
    # Turnover-constrained rebalance
    # ------------------------------------------------------------------

    @staticmethod
    def constrained_rebalance(
        target_weights: np.ndarray,
        current_weights: np.ndarray,
        max_turnover: float = 0.3,
    ) -> np.ndarray:
        """Apply turnover constraint to target weights.

        If total turnover exceeds max_turnover, scale the trade towards
        current weights proportionally.

        Parameters
        ----------
        target_weights : desired new weights.
        current_weights : current portfolio weights.
        max_turnover : max allowed one-way turnover (sum of sells).

        Returns
        -------
        Constrained weights that respect the turnover limit.
        """
        trade = target_weights - current_weights
        turnover = np.sum(np.abs(trade)) / 2  # one-way

        if turnover <= max_turnover:
            return target_weights

        # Scale trade to fit within turnover budget
        scale = max_turnover / turnover
        new_weights = current_weights + scale * trade
        # Renormalise
        new_weights = new_weights / np.sum(new_weights)
        return new_weights
