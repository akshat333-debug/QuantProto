"""Backtrader adapter.

Extracts returns from a Backtrader strategy result and audits them.

Typical usage
-------------
>>> import backtrader as bt
>>> cerebro = bt.Cerebro()
>>> cerebro.addstrategy(MyStrategy)
>>> cerebro.adddata(data)
>>> cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")
>>> cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
>>> result = cerebro.run()
>>> from quantproto.adapters import audit_backtrader
>>> report = audit_backtrader(result)
>>> print(report["score"], report["verdict"])

Without analyzers
-----------------
If you already have a portfolio-value Series (e.g. from a custom observer),
pass it directly via ``equity``:

>>> report = audit_backtrader(None, equity=portfolio_values)
"""

from __future__ import annotations

from typing import Any

import numpy as np

from quantproto.adapters.base import _equity_series_to_returns, audit_returns
from quantproto.integrity.score import robustness_report


def audit_backtrader(
    result,
    *,
    strategy_index: int = 0,
    analyzer_name: str = "time_return",
    equity=None,
    n_trials: int = 1,
    turnover: float = 1.0,
    variant_matrix=None,
    n_splits: int = 16,
) -> dict[str, Any]:
    """Audit a Backtrader cerebro result.

    Parameters
    ----------
    result : list returned by ``cerebro.run()``.  Pass ``None`` if you
        are supplying ``equity`` directly.
    strategy_index : which strategy in the result list to audit (default 0).
    analyzer_name : name of the ``bt.analyzers.TimeReturn`` analyzer added
        to the cerebro (default ``"time_return"``).
    equity : optional portfolio-value Series or list to use instead of the
        TimeReturn analyzer (useful when no analyzer was added).
    n_trials : configurations tried before picking this one.
    turnover : average one-way turnover per period.
    variant_matrix : (T, N) returns of all tried configurations (for PBO).
    n_splits : CSCV blocks.

    Returns
    -------
    Full robustness report dict.
    """
    returns_arr = _extract_returns(result, strategy_index, analyzer_name, equity)
    avg_turnover = _extract_turnover(result, strategy_index) or turnover

    return robustness_report(
        returns_arr,
        n_trials=n_trials,
        turnover=avg_turnover,
        variant_matrix=variant_matrix,
        n_splits=n_splits,
    )


def _extract_returns(result, idx: int, analyzer_name: str, equity) -> np.ndarray:
    if equity is not None:
        return _equity_series_to_returns(equity)

    if result is None:
        raise ValueError(
            "Pass either a cerebro.run() result or equity= to audit_backtrader()"
        )

    try:
        strat = result[idx]
    except (IndexError, TypeError) as exc:
        raise ValueError(
            f"result[{idx}] not accessible — pass the list returned by cerebro.run()"
        ) from exc

    # Try TimeReturn analyzer first (most accurate)
    try:
        analysis = strat.analyzers.__dict__.get(
            analyzer_name,
            getattr(strat.analyzers, analyzer_name, None),
        )
        if analysis is None:
            raise AttributeError
        rets = analysis.get_analysis()
        values = list(rets.values())
        if values:
            return np.asarray(values, dtype=float)
    except (AttributeError, KeyError):
        pass

    # Fallback: look for any TimeReturn-like analyzer
    try:
        for name in dir(strat.analyzers):
            a = getattr(strat.analyzers, name, None)
            if a is None:
                continue
            try:
                ana = a.get_analysis()
                if isinstance(ana, dict) and ana:
                    values = list(ana.values())
                    if all(isinstance(v, (int, float)) for v in values):
                        return np.asarray(values, dtype=float)
            except Exception:
                continue
    except Exception:
        pass

    raise ValueError(
        "Could not extract returns from the Backtrader result.  "
        "Add bt.analyzers.TimeReturn(timeframe=bt.TimeFrame.Days) to your cerebro "
        "before running, or pass equity= with a portfolio-value series."
    )


def _extract_turnover(result, idx: int) -> float | None:
    """Estimate turnover from TradeAnalyzer if available."""
    try:
        strat = result[idx]
        for name in dir(strat.analyzers):
            a = getattr(strat.analyzers, name, None)
            if a is None:
                continue
            try:
                ana = a.get_analysis()
                if hasattr(ana, "total") and hasattr(ana.total, "total"):
                    n_trades = int(ana.total.total or 0)
                    n_bars = len(strat.data)
                    if n_bars > 0 and n_trades > 0:
                        return float(n_trades) / n_bars
            except Exception:
                continue
    except Exception:
        pass
    return None
