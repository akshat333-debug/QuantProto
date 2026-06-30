"""Backtest-integrity & overfitting audit engine.

The flagship of QuantProto: rigorous, agent-callable checks for whether a
strategy's backtested edge is real or an artefact of overfitting.

- Deflated / Probabilistic Sharpe Ratio (multiple-testing + non-normality)
- Probability of Backtest Overfitting via CSCV
- Purged & embargoed cross-validation (leak-free OOS)
- Transaction-cost sensitivity & break-even
- Statistical red-flag detection + manual integrity checklist
- A single Robustness Score (0–100) with a plain-English verdict

Works on QuantProto's own pipeline *and* on any bring-your-own backtest.
"""

from quantproto.integrity.deflated_sharpe import (
    probabilistic_sharpe_ratio,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    minimum_track_record_length,
    analyze_returns,
)
from quantproto.integrity.pbo import pbo_cscv
from quantproto.integrity.purged_cv import PurgedKFold
from quantproto.integrity.cost_sensitivity import cost_sensitivity_sweep
from quantproto.integrity.bias_checks import detect_red_flags, integrity_checklist
from quantproto.integrity.score import robustness_report

__all__ = [
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
    "expected_max_sharpe",
    "minimum_track_record_length",
    "analyze_returns",
    "pbo_cscv",
    "PurgedKFold",
    "cost_sensitivity_sweep",
    "detect_red_flags",
    "integrity_checklist",
    "robustness_report",
]
