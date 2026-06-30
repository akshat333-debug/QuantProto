"""Zipline / Zipline-Reloaded adapter.

Extracts returns from a Zipline ``perf`` DataFrame and audits them.

Usage
-----
>>> from zipline import run_algorithm
>>> perf = run_algorithm(...)          # returns a pd.DataFrame
>>> from quantproto.adapters import audit_zipline
>>> report = audit_zipline(perf)
>>> print(report["score"], report["verdict"])

The ``perf`` DataFrame is the standard output of Zipline's
``run_algorithm()`` function.  It has at minimum a ``portfolio_value``
column (and optionally ``returns``, ``gross_leverage``, etc.).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from quantproto.adapters.base import _equity_series_to_returns, _coerce
from quantproto.integrity.score import robustness_report


def audit_zipline(
    perf,
    *,
    n_trials: int = 1,
    turnover: float = 1.0,
    variant_matrix=None,
    n_splits: int = 16,
) -> dict[str, Any]:
    """Audit a Zipline backtest performance DataFrame.

    Parameters
    ----------
    perf : pd.DataFrame returned by ``zipline.run_algorithm()``.
        Must have either a ``returns`` or ``portfolio_value`` column.
    n_trials : configurations tried before picking this one.
    turnover : average one-way turnover per period.
    variant_matrix : (T, N) returns of all tried configurations (for PBO).
    n_splits : CSCV blocks.

    Returns
    -------
    Full robustness report dict.
    """
    returns_arr, avg_turnover = _extract(perf)
    return robustness_report(
        returns_arr,
        n_trials=n_trials,
        turnover=avg_turnover or turnover,
        variant_matrix=variant_matrix,
        n_splits=n_splits,
    )


def _extract(perf):
    try:
        import pandas as pd  # noqa: PLC0415
        if not isinstance(perf, pd.DataFrame):
            raise TypeError
    except ImportError:
        raise ImportError("pandas is required to use audit_zipline()")
    except TypeError:
        raise ValueError(
            "Expected a pd.DataFrame from zipline.run_algorithm(). "
            "Pass the object returned by run_algorithm() directly."
        )

    # Prefer the pre-computed 'returns' column (per-day simple returns)
    if "returns" in perf.columns:
        arr = _coerce(perf["returns"].dropna())
        if arr.size >= 2:
            avg_turnover = _turnover_from_perf(perf)
            return arr, avg_turnover

    # Fallback: derive from portfolio_value
    if "portfolio_value" in perf.columns:
        arr = _equity_series_to_returns(perf["portfolio_value"].dropna())
        avg_turnover = _turnover_from_perf(perf)
        return arr, avg_turnover

    raise ValueError(
        "The Zipline perf DataFrame must have a 'returns' or 'portfolio_value' "
        "column. Got columns: " + str(list(perf.columns))
    )


def _turnover_from_perf(perf) -> float | None:
    """Estimate daily one-way turnover from 'gross_leverage' changes."""
    try:
        if "gross_leverage" in perf.columns:
            lev = perf["gross_leverage"].dropna()
            daily_change = lev.diff().abs().mean()
            return float(daily_change) if np.isfinite(daily_change) else None
    except Exception:
        pass
    return None
