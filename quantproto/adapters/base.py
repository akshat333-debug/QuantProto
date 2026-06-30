"""Shared utilities for framework adapters."""

from __future__ import annotations

from typing import Any

import numpy as np

from quantproto.integrity.score import robustness_report
from quantproto.integrity.ingest import parse_returns, equity_to_returns


def audit_returns(
    returns,
    *,
    n_trials: int = 1,
    turnover: float = 1.0,
    variant_matrix=None,
    n_splits: int = 16,
) -> dict[str, Any]:
    """Audit a plain return series from any source.

    Parameters
    ----------
    returns : list, np.ndarray, or pd.Series of per-period returns.
    n_trials : configurations tried before picking this one.
    turnover : average one-way turnover per period.
    variant_matrix : (T, N) returns for all tried configurations (for PBO).
    n_splits : CSCV blocks.

    Returns
    -------
    Full robustness report dict.  See ``robustness_report`` for field docs.
    """
    arr = _coerce(returns)
    return robustness_report(
        arr,
        n_trials=n_trials,
        turnover=turnover,
        variant_matrix=variant_matrix,
        n_splits=n_splits,
    )


def _coerce(values) -> np.ndarray:
    """Convert list / Series / ndarray → float64 ndarray."""
    try:
        import pandas as pd  # noqa: PLC0415
        if isinstance(values, pd.Series):
            return values.dropna().to_numpy(dtype=float)
    except ImportError:
        pass
    return parse_returns(list(values))


def _equity_series_to_returns(equity) -> np.ndarray:
    """Convert any equity / NAV series to per-period returns."""
    try:
        import pandas as pd  # noqa: PLC0415
        if isinstance(equity, pd.Series):
            eq = equity.dropna().to_numpy(dtype=float)
            if np.any(eq <= 0):
                raise ValueError("equity_curve: values must be positive")
            return np.diff(eq) / eq[:-1]
    except ImportError:
        pass
    return equity_to_returns(list(equity))
