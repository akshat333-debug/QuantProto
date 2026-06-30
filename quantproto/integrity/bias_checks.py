"""Statistical red-flag detection for backtest return series.

Some backtest lies leave a statistical fingerprint in the return series
itself (an implausibly high Sharpe, a suspiciously smooth equity curve, a
sample too short to mean anything). Others — survivorship bias, lookahead
bias, point-in-time data errors — cannot be proven from returns alone and
must be confirmed against the *construction* of the backtest.

This module is deliberately honest about that distinction:
- :func:`detect_red_flags` returns evidence-based flags from the series.
- :func:`integrity_checklist` returns the items a human must verify manually.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import skew as _skew, kurtosis as _kurtosis

PERIODS_PER_YEAR = 252


def detect_red_flags(returns: np.ndarray) -> list[dict]:
    """Return a list of statistical red flags found in the return series.

    Each flag is ``{"severity": "high|medium|low", "code": str,
    "message": str}``. An empty list means nothing suspicious was detected
    (which is *not* a guarantee of robustness — see :func:`integrity_checklist`).
    """
    r = np.asarray(returns, dtype=float)
    n = r.size
    flags: list[dict] = []

    if n < 60:
        flags.append({
            "severity": "high",
            "code": "short_sample",
            "message": f"Only {n} observations — far too few to trust any Sharpe. "
                       "Sharpe estimates need hundreds of points to stabilise.",
        })
    elif n < 252:
        flags.append({
            "severity": "medium",
            "code": "modest_sample",
            "message": f"{n} observations (< 1 year of daily data) — Sharpe "
                       "confidence intervals will be wide.",
        })

    std = np.std(r, ddof=1)
    sharpe_ann = 0.0 if std < 1e-12 else float(np.mean(r) / std * np.sqrt(PERIODS_PER_YEAR))

    if sharpe_ann > 4.0:
        flags.append({
            "severity": "high",
            "code": "implausible_sharpe",
            "message": f"Annualised Sharpe of {sharpe_ann:.1f} is implausibly high "
                       "for a real strategy — a classic signature of lookahead "
                       "bias or curve-fitting.",
        })
    elif sharpe_ann > 3.0:
        flags.append({
            "severity": "medium",
            "code": "high_sharpe",
            "message": f"Annualised Sharpe of {sharpe_ann:.1f} is very high — verify "
                       "it survives realistic costs and out-of-sample data.",
        })

    if n > 3:
        g3 = float(_skew(r, bias=False))
        g4 = float(_kurtosis(r, fisher=False, bias=False))
        if g3 < -0.5:
            flags.append({
                "severity": "medium",
                "code": "negative_skew",
                "message": f"Negative skew ({g3:.2f}): returns hide tail risk — "
                           "rare large losses that a naive Sharpe understates.",
            })
        if g4 > 6.0:
            flags.append({
                "severity": "medium",
                "code": "fat_tails",
                "message": f"High kurtosis ({g4:.1f}): fat tails make extreme moves "
                           "far more likely than a normal distribution implies.",
            })

    # Suspiciously smooth equity: strong positive autocorrelation of returns
    # is a hallmark of stale marks, interpolation, or lookahead.
    if n > 10:
        ac1 = _autocorr(r, 1)
        if ac1 > 0.3:
            flags.append({
                "severity": "high",
                "code": "smooth_equity",
                "message": f"Return autocorrelation of {ac1:.2f} — the equity curve "
                           "is unrealistically smooth. Check for stale prices, "
                           "overlapping windows, or lookahead.",
            })

    # Implausible win rate combined with a positive mean.
    if n >= 60:
        win_rate = float(np.mean(r > 0))
        if win_rate > 0.75 and np.mean(r) > 0:
            flags.append({
                "severity": "medium",
                "code": "high_win_rate",
                "message": f"Win rate of {win_rate:.0%} is suspiciously high — "
                           "confirm the backtest is not peeking at future data.",
            })

    return flags


def _autocorr(r: np.ndarray, lag: int) -> float:
    if r.size <= lag:
        return 0.0
    a = r[:-lag] - r.mean()
    b = r[lag:] - r.mean()
    denom = np.sqrt(np.sum(a**2) * np.sum(b**2))
    if denom < 1e-12:
        return 0.0
    return float(np.sum(a * b) / denom)


def integrity_checklist() -> list[dict]:
    """Items that cannot be verified from returns and need manual confirmation.

    Returned as structured, unresolved checklist entries so the UI / agent can
    prompt the user rather than imply false certainty.
    """
    return [
        {
            "code": "survivorship",
            "question": "Does the universe include delisted / bankrupt / acquired "
                        "names that existed during the test period?",
            "why": "Testing only on today's survivors overstates returns "
                   "(~0.9%/yr in funds; larger in single stocks).",
        },
        {
            "code": "lookahead",
            "question": "Are all signals computed strictly from data available "
                        "before the trade timestamp (point-in-time)?",
            "why": "A single one-bar lookahead can turn a loser into an apparent "
                   "Sharpe-3 winner.",
        },
        {
            "code": "costs",
            "question": "Do returns already net out commissions, spread, slippage, "
                        "and market impact at realistic participation?",
            "why": "Zero-cost assumptions inflate every strategy; see the "
                   "cost-sensitivity break-even.",
        },
        {
            "code": "capacity",
            "question": "Is the strategy's capital capacity consistent with the "
                        "liquidity of the traded universe?",
            "why": "Backtests assume infinite liquidity; live fills do not.",
        },
    ]
