"""bt (Pmorales) adapter.

Extracts returns from a ``bt.Result`` object and audits them.

Usage
-----
>>> import bt
>>> s = bt.Strategy("my_strategy", [bt.algos.WeighEqually(), bt.algos.Rebalance()])
>>> bt_result = bt.run(bt.Backtest(s, data))
>>> from quantproto.adapters import audit_bt
>>> report = audit_bt(bt_result)
>>> print(report["score"], report["verdict"])

Or use the first strategy's equity directly:

>>> report = audit_bt(bt_result, strategy_name="my_strategy")
"""

from __future__ import annotations

from typing import Any

import numpy as np

from quantproto.adapters.base import _equity_series_to_returns, _coerce
from quantproto.integrity.score import robustness_report


def audit_bt(
    result,
    *,
    strategy_name: str | None = None,
    n_trials: int = 1,
    turnover: float = 1.0,
    variant_matrix=None,
    n_splits: int = 16,
) -> dict[str, Any]:
    """Audit a bt.Result object.

    Parameters
    ----------
    result : ``bt.Result`` returned by ``bt.run()``.
    strategy_name : which strategy in the result to audit (default: first).
    n_trials : configurations tried before picking this one.
    turnover : average one-way turnover per period.
    variant_matrix : (T, N) returns of all tried configurations (for PBO).
    n_splits : CSCV blocks.

    Returns
    -------
    Full robustness report dict.
    """
    returns_arr, avg_turnover = _extract(result, strategy_name)
    return robustness_report(
        returns_arr,
        n_trials=n_trials,
        turnover=avg_turnover or turnover,
        variant_matrix=variant_matrix,
        n_splits=n_splits,
    )


def _extract(result, strategy_name: str | None):
    # bt.Result has .prices (portfolio NAV over time) and .stats
    # result.prices is a pd.DataFrame with strategy names as columns
    try:
        prices = result.prices  # pd.DataFrame
    except AttributeError:
        raise ValueError(
            "Expected a bt.Result object with a .prices attribute. "
            "Pass the object returned by bt.run()."
        )

    if prices is None or prices.empty:
        raise ValueError("bt.Result.prices is empty — run the backtest first.")

    if strategy_name is not None:
        if strategy_name not in prices.columns:
            raise ValueError(
                f"Strategy '{strategy_name}' not found in bt.Result. "
                f"Available: {list(prices.columns)}"
            )
        equity = prices[strategy_name].dropna()
    else:
        equity = prices.iloc[:, 0].dropna()

    returns_arr = _equity_series_to_returns(equity)

    # Estimate turnover from stats if available
    avg_turnover = None
    try:
        stats = result.stats
        col = strategy_name or stats.columns[0]
        to = stats.loc["turnover", col] if "turnover" in stats.index else None
        if to is not None and np.isfinite(float(to)):
            avg_turnover = float(to)
    except Exception:
        pass

    return returns_arr, avg_turnover
