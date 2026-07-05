"""Live-vs-backtest drift monitor.

Allocators' recurring complaint (see docs/tracker-design.md): live performance
underperforms backtests ~50% on average, and nothing tells you *when* the gap
crosses from normal noise into "this edge decayed". This module answers that
with the same PSR machinery used for the research-budget meter, applied
two-sample: is live's Sharpe statistically consistent with the backtest's, or
has it diverged beyond what sampling noise explains?

Live fills are logged into the same ledger (source="live") for provenance, but
excluded from the research-budget's config search — they are not a new
strategy variant, they're the deployed one's real-world track record.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import skew as _skew, kurtosis as _kurtosis

from quantproto.integrity.deflated_sharpe import probabilistic_sharpe_ratio

ANNUALIZE = float(np.sqrt(252))
MIN_LIVE_OBS = 20


def _sharpe(r: np.ndarray) -> float:
    std = np.std(r, ddof=1) if r.size > 1 else 0.0
    return 0.0 if std < 1e-12 else float(np.mean(r) / std)


def live_consistency(
    backtest_returns: np.ndarray,
    live_returns: np.ndarray,
    target_prob: float = 0.95,
) -> dict:
    """Test whether live returns are consistent with the backtest distribution.

    Computes the live-sample Sharpe's Probabilistic Sharpe Ratio against the
    *backtest* Sharpe as benchmark: PSR(live_sharpe >= backtest_sharpe). A low
    value means live is statistically underperforming the backtest — the
    classic decay/overfit-in-hindsight signature — beyond what live's own
    sample noise would explain.
    """
    bt = np.asarray(backtest_returns, dtype=float)
    live = np.asarray(live_returns, dtype=float)

    if live.size < MIN_LIVE_OBS:
        return {
            "state": "insufficient_data",
            "n_live": int(live.size),
            "message": f"Only {live.size} live observations logged; need ≥ {MIN_LIVE_OBS} "
                       "before drift can be assessed.",
        }

    bt_sr = _sharpe(bt)
    live_sr = _sharpe(live)
    g3 = float(_skew(live, bias=False)) if live.size > 2 else 0.0
    g4 = float(_kurtosis(live, fisher=False, bias=False)) if live.size > 3 else 3.0

    # P(true live Sharpe >= backtest Sharpe), given live's own sample size/shape.
    consistency = probabilistic_sharpe_ratio(live_sr, live.size, g3, g4, bt_sr)

    if consistency < 1.0 - target_prob:
        state = "diverging"
        message = (
            f"Live Sharpe ({live_sr * ANNUALIZE:.2f} ann.) is statistically below the "
            f"backtest's ({bt_sr * ANNUALIZE:.2f} ann.) — only {consistency:.1%} probability "
            "this is sampling noise. Treat the backtested edge as decayed until live recovers."
        )
    elif consistency < target_prob:
        state = "watch"
        message = (
            f"Live Sharpe ({live_sr * ANNUALIZE:.2f} ann.) trails the backtest "
            f"({bt_sr * ANNUALIZE:.2f} ann.) but not yet outside sampling noise "
            f"({consistency:.1%} consistent). Keep watching."
        )
    else:
        state = "consistent"
        message = (
            f"Live Sharpe ({live_sr * ANNUALIZE:.2f} ann.) is statistically consistent with "
            f"the backtest ({bt_sr * ANNUALIZE:.2f} ann.); no evidence of decay."
        )

    return {
        "state": state,
        "n_live": int(live.size),
        "n_backtest": int(bt.size),
        "backtest_sharpe_ann": round(bt_sr * ANNUALIZE, 3),
        "live_sharpe_ann": round(live_sr * ANNUALIZE, 3),
        "consistency_prob": round(consistency, 4),
        "message": message,
    }
