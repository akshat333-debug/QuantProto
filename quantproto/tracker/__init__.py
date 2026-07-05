"""Backtest experiment tracker — the ledger that makes overfitting math honest.

Deflated Sharpe and PBO need one input nobody has: how many configurations were
actually tried. This package captures every backtest run (params + returns) into
a hash-chained ledger and recomputes the "research budget" — expected spurious
Sharpe, DSR, PBO, haircut — as the search proceeds, so the trial count is
observed rather than self-reported.

Entry point::

    import quantproto as qp
    exp = qp.experiment("spy-meanrev")
    with exp.run(params={"lookback": 20}) as run:
        run.log_returns(daily_returns)
    exp.status()   # research-budget meter
"""

from quantproto.tracker.ledger import RunLedger
from quantproto.tracker.experiment import Experiment, experiment
from quantproto.tracker.budget import research_budget, parameter_sensitivity
from quantproto.tracker.drift import live_consistency

__all__ = [
    "RunLedger",
    "Experiment",
    "experiment",
    "research_budget",
    "parameter_sensitivity",
    "live_consistency",
]
