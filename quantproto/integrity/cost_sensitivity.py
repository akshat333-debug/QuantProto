"""Transaction-cost sensitivity analysis.

The single most common way a backtest lies is by assuming zero trading cost.
This module answers the question allocators actually ask: *at what cost level
does this edge die?* It sweeps a grid of per-trade cost assumptions, recomputes
the net annualised Sharpe at each, and reports the break-even cost in basis
points — the cost at which the strategy's Sharpe crosses zero.

Reuses the basis-point cost convention from
:mod:`quantproto.execution_model` (``cost = notional × bps / 10_000``); here it
is applied per period as ``turnover × bps / 10_000``.
"""

from __future__ import annotations

import numpy as np

PERIODS_PER_YEAR = 252


def _annualized_sharpe(returns: np.ndarray) -> float:
    std = np.std(returns, ddof=1)
    if std < 1e-12:
        return 0.0
    return float(np.mean(returns) / std * np.sqrt(PERIODS_PER_YEAR))


def cost_sensitivity_sweep(
    returns: np.ndarray,
    turnover: float = 1.0,
    bps_grid: list[float] | None = None,
) -> dict:
    """Sweep trading-cost assumptions and find the break-even cost.

    Parameters
    ----------
    returns : gross per-period strategy returns.
    turnover : average one-way turnover per period (1.0 = fully rotate the book
        every period; 0.1 = 10 % of book traded per period).
    bps_grid : cost levels in basis points to evaluate.
        Defaults to ``[0, 1, 2, 5, 10, 20, 50, 100]``.

    Returns
    -------
    {
        "bps_grid": [float],
        "net_sharpe": [float],       # annualised net Sharpe at each cost
        "gross_sharpe": float,
        "breakeven_bps": float,      # cost where net Sharpe = 0 (inf if never)
        "turnover": float,
    }
    """
    r = np.asarray(returns, dtype=float)
    if bps_grid is None:
        bps_grid = [0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
    bps_grid = sorted(float(b) for b in bps_grid)

    gross_sharpe = _annualized_sharpe(r)
    net_sharpe = []
    for bps in bps_grid:
        cost_per_period = turnover * bps / 10_000.0
        net_sharpe.append(_annualized_sharpe(r - cost_per_period))

    breakeven = _breakeven_bps(r, turnover, gross_sharpe)

    return {
        "bps_grid": bps_grid,
        "net_sharpe": net_sharpe,
        "gross_sharpe": gross_sharpe,
        "breakeven_bps": breakeven,
        "turnover": turnover,
    }


def _breakeven_bps(returns: np.ndarray, turnover: float, gross_sharpe: float) -> float:
    """Cost (bps) at which annualised Sharpe hits zero.

    Net Sharpe is monotonically decreasing in cost, and the mean return is
    linear in cost, so the break-even is closed-form:
    mean(r) − turnover·bps/1e4 = 0  →  bps = mean(r)·1e4 / turnover.
    """
    if gross_sharpe <= 0 or turnover <= 0:
        return 0.0 if gross_sharpe <= 0 else float("inf")
    mean_r = float(np.mean(returns))
    if mean_r <= 0:
        return 0.0
    return mean_r * 10_000.0 / turnover
