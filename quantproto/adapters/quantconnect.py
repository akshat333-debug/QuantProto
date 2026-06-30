"""QuantConnect adapter.

Extracts returns from a QuantConnect backtest result and audits them.

QuantConnect result formats accepted
-------------------------------------
1. **JSON result dict** (from the QC REST API or downloaded from the cloud IDE):

   >>> import json, requests
   >>> result = json.loads(open("backtest.json").read())
   >>> from quantproto.adapters import audit_quantconnect
   >>> report = audit_quantconnect(result)

2. **CSV equity export** (paste the equity column as a list or Series):

   >>> report = audit_quantconnect(None, equity=equity_values)

3. **QC Statistics dict** (the `Statistics` key from a result):

   >>> report = audit_quantconnect({"Statistics": {...}, "Charts": {...}})
"""

from __future__ import annotations

from typing import Any

import numpy as np

from quantproto.adapters.base import _equity_series_to_returns
from quantproto.integrity.score import robustness_report


# Paths tried when navigating the QC result JSON for the equity curve.
_EQUITY_PATHS = [
    # Full JSON result from the REST API
    ("Charts", "Strategy Equity", "Series", "Equity", "Values"),
    # Lean local JSON result
    ("charts", "Strategy Equity", "series", "Equity", "values"),
    # Sometimes nested under Backtest
    ("Backtest", "Charts", "Strategy Equity", "Series", "Equity", "Values"),
]


def audit_quantconnect(
    result: dict | None,
    *,
    equity=None,
    n_trials: int = 1,
    turnover: float = 1.0,
    variant_matrix=None,
    n_splits: int = 16,
) -> dict[str, Any]:
    """Audit a QuantConnect backtest result.

    Parameters
    ----------
    result : QuantConnect result dict (from the cloud IDE JSON download or
        the REST API).  Pass ``None`` if you are supplying ``equity`` directly.
    equity : optional equity-curve list / Series to use instead of
        parsing the result dict.
    n_trials : configurations tried before picking this one.
    turnover : average one-way turnover per period.
    variant_matrix : (T, N) returns of all tried configurations (for PBO).
    n_splits : CSCV blocks.

    Returns
    -------
    Full robustness report dict.
    """
    returns_arr = _extract_returns(result, equity)
    avg_turnover = _extract_turnover(result) or turnover

    return robustness_report(
        returns_arr,
        n_trials=n_trials,
        turnover=avg_turnover,
        variant_matrix=variant_matrix,
        n_splits=n_splits,
    )


def _extract_returns(result: dict | None, equity) -> np.ndarray:
    if equity is not None:
        return _equity_series_to_returns(equity)

    if result is None:
        raise ValueError(
            "Pass either a QC result dict or equity= to audit_quantconnect()"
        )

    # Try each known path to the equity series
    for path in _EQUITY_PATHS:
        node = result
        for key in path:
            if not isinstance(node, dict) or key not in node:
                node = None
                break
            node = node[key]
        if node is not None:
            eq = _parse_qc_equity(node)
            if eq is not None:
                return eq

    # Try a flat "equity" or "Equity" top-level key
    for key in ("equity", "Equity", "EquityCurve", "equity_curve"):
        if key in result:
            vals = result[key]
            if isinstance(vals, (list, tuple)) and vals:
                return _equity_series_to_returns(_numeric_list(vals))

    raise ValueError(
        "Could not find an equity curve in the QuantConnect result dict. "
        "Expected Charts → Strategy Equity → Series → Equity → Values. "
        "Download the full JSON result from the QC cloud IDE, or pass "
        "equity= with the portfolio-value series."
    )


def _parse_qc_equity(values) -> np.ndarray | None:
    """Parse QC equity values: list of {x, y} dicts or plain numbers."""
    if not isinstance(values, (list, tuple)) or not values:
        return None

    first = values[0]
    if isinstance(first, dict):
        # {"x": timestamp_ms, "y": equity_value}
        ys = [v.get("y", v.get("Y", None)) for v in values]
        ys = [y for y in ys if y is not None]
    elif isinstance(first, (int, float)):
        ys = list(values)
    else:
        return None

    if not ys:
        return None
    return _equity_series_to_returns(np.asarray(ys, dtype=float))


def _numeric_list(values) -> list[float]:
    out = []
    for v in values:
        if isinstance(v, dict):
            y = v.get("y", v.get("Y", v.get("value", None)))
            if y is not None:
                out.append(float(y))
        elif isinstance(v, (int, float)):
            out.append(float(v))
    return out


def _extract_turnover(result: dict | None) -> float | None:
    if not isinstance(result, dict):
        return None
    stats = result.get("Statistics", result.get("statistics", {}))
    if not isinstance(stats, dict):
        return None
    # QC uses "Turnover" in Statistics (annual fraction)
    for key in ("Turnover", "turnover", "AnnualTurnover", "Annual Turnover"):
        val = stats.get(key)
        if val is not None:
            try:
                raw = str(val).replace("%", "").strip()
                pct = float(raw)
                # QC reports annual turnover as %; convert to daily one-way
                return pct / 100.0 / 252.0
            except (ValueError, TypeError):
                pass
    return None
