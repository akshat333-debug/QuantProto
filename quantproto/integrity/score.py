"""Robustness Score — the single verdict that ties the audit together.

Blends the academic integrity statistics (Probabilistic / Deflated Sharpe,
Probability of Backtest Overfitting, cost break-even, sample adequacy) and the
statistical red flags into one 0–100 score with a plain-English verdict:

    ≥ 70  → robust       (edge is plausibly real)
    40–69 → fragile      (edge is uncertain; stress it further)
    < 40  → likely overfit (treat the backtest as noise)

This is the new **Research Integrity Gate** — the honest replacement for a bare
Sharpe number. It is exposed via MCP (``robustness_audit``), the dashboard
(Integrity tab + bring-your-own panel), and folded into the agent pipeline's
go/no-go decision.
"""

from __future__ import annotations

import numpy as np

from quantproto.integrity.deflated_sharpe import analyze_returns, _sample_stats
from quantproto.integrity.cost_sensitivity import cost_sensitivity_sweep
from quantproto.integrity.bias_checks import detect_red_flags, integrity_checklist
from quantproto.integrity.pbo import pbo_cscv

# Component weights (sum to 100 before red-flag penalties).
W_SIGNIFICANCE = 35.0   # Probabilistic Sharpe (is the edge statistically real?)
W_SELECTION = 30.0      # PBO / Deflated Sharpe (was it cherry-picked?)
W_COST = 20.0           # Does it survive realistic trading costs?
W_SAMPLE = 15.0         # Is the track record long enough to trust?

BREAKEVEN_TARGET_BPS = 30.0  # break-even at/above this earns full cost credit
PENALTY = {"high": 12.0, "medium": 5.0, "low": 2.0}


def _variant_var_sharpe(variant_matrix: np.ndarray) -> float:
    """Variance of per-period Sharpe across strategy variants (for deflation)."""
    sharpes = []
    for j in range(variant_matrix.shape[1]):
        col = variant_matrix[:, j]
        std = np.std(col, ddof=1)
        sharpes.append(0.0 if std < 1e-12 else np.mean(col) / std)
    return float(np.var(sharpes, ddof=1)) if len(sharpes) > 1 else 0.0


def robustness_report(
    returns,
    n_trials: int = 1,
    turnover: float = 1.0,
    variant_matrix=None,
    var_sharpe: float | None = None,
    n_splits: int = 16,
) -> dict:
    """Run the full integrity audit on a return series.

    Parameters
    ----------
    returns : per-period returns of the strategy under audit.
    n_trials : how many strategy configurations were tried before selecting
        this one (drives the Deflated Sharpe multiple-testing correction).
    turnover : average one-way turnover per period (drives cost sensitivity).
    variant_matrix : optional (T, N) returns of all tried variants. When
        supplied, PBO is computed and ``var_sharpe`` / ``n_trials`` are inferred.
    var_sharpe : optional variance of Sharpe across trials for the Deflated
        Sharpe (inferred from ``variant_matrix`` if that is given).
    n_splits : CSCV blocks for PBO.

    Returns
    -------
    A structured report: score, verdict, per-component breakdown, the
    underlying statistics, red flags, and the manual checklist.
    """
    r = np.asarray(returns, dtype=float)
    if r.size < 2:
        raise ValueError("Need at least 2 return observations to audit")

    # ── PBO (only meaningful with a variant matrix) ───────────────────────
    pbo_result = None
    if variant_matrix is not None:
        vm = np.asarray(variant_matrix, dtype=float)
        if vm.ndim == 2 and vm.shape[1] >= 2:
            pbo_result = pbo_cscv(vm, n_splits=n_splits)
            if var_sharpe is None:
                var_sharpe = _variant_var_sharpe(vm)
            n_trials = max(n_trials, vm.shape[1])

    # ── Deflated / Probabilistic Sharpe + sample adequacy ────────────────
    dsr_stats = analyze_returns(r, n_trials=n_trials, var_sharpe=var_sharpe)
    # ── Cost sensitivity ─────────────────────────────────────────────────
    cost = cost_sensitivity_sweep(r, turnover=turnover)
    # ── Red flags + manual checklist ─────────────────────────────────────
    flags = detect_red_flags(r)
    checklist = integrity_checklist()

    # ── Component scoring ─────────────────────────────────────────────────
    # Significance reflects whether the edge is statistically real. When we
    # know a search happened (variant matrix or declared trials + variance),
    # we score the *deflated* Sharpe — the raw in-sample PSR is precisely the
    # illusion overfitting creates, so trusting it would defeat the purpose.
    psr = dsr_stats["psr"]
    dsr_val = dsr_stats["dsr"]  # None when no multiple-testing info supplied
    sig_basis = dsr_val if dsr_val is not None else psr
    sig_score = sig_basis * W_SIGNIFICANCE

    notes: list[str] = []
    if pbo_result is not None:
        sel_score = (1.0 - pbo_result["pbo"]) * W_SELECTION
    elif dsr_val is not None:
        sel_score = dsr_val * W_SELECTION
    else:
        # No multiple-testing information available — give partial, discounted
        # credit and flag the gap rather than implying it was assessed.
        sel_score = psr * W_SELECTION * 0.7
        notes.append(
            "Selection-bias not fully assessed: supply the strategy-variant "
            "matrix (for PBO) or the number of trials + Sharpe variance (for "
            "Deflated Sharpe) to harden this component."
        )

    breakeven = cost["breakeven_bps"]
    if not np.isfinite(breakeven):
        cost_frac = 1.0
    else:
        cost_frac = float(np.clip(breakeven / BREAKEVEN_TARGET_BPS, 0.0, 1.0))
    cost_score = cost_frac * W_COST

    min_trl = dsr_stats["min_track_record_length"]
    n_obs = dsr_stats["n_obs"]
    if not np.isfinite(min_trl):
        sample_frac = 0.0  # no edge → no track record length suffices
    else:
        sample_frac = float(np.clip(n_obs / min_trl, 0.0, 1.0))
    sample_score = sample_frac * W_SAMPLE

    raw_score = sig_score + sel_score + cost_score + sample_score
    penalty = sum(PENALTY.get(f["severity"], 0.0) for f in flags)
    score = float(np.clip(raw_score - penalty, 0.0, 100.0))

    if score >= 70:
        verdict, headline = "robust", "Edge is plausibly real."
    elif score >= 40:
        verdict, headline = "fragile", "Edge is uncertain — stress it further before trusting it."
    else:
        verdict, headline = "likely_overfit", "Treat this backtest as noise until proven otherwise."

    return {
        "score": round(score, 1),
        "verdict": verdict,
        "headline": headline,
        "components": {
            "significance": round(sig_score, 1),
            "selection": round(sel_score, 1),
            "cost_survival": round(cost_score, 1),
            "sample_adequacy": round(sample_score, 1),
            "red_flag_penalty": round(penalty, 1),
            "max": {
                "significance": W_SIGNIFICANCE,
                "selection": W_SELECTION,
                "cost_survival": W_COST,
                "sample_adequacy": W_SAMPLE,
            },
        },
        "statistics": {
            "sharpe_annualized": round(dsr_stats["sharpe_annualized"], 3),
            "psr": round(psr, 4),
            "dsr": None if dsr_stats["dsr"] is None else round(dsr_stats["dsr"], 4),
            "skew": round(dsr_stats["skew"], 3),
            "kurtosis": round(dsr_stats["kurtosis"], 3),
            "n_obs": n_obs,
            "n_trials": n_trials,
            "min_track_record_length": None if not np.isfinite(min_trl) else round(min_trl, 1),
            "breakeven_bps": None if not np.isfinite(breakeven) else round(breakeven, 2),
        },
        "pbo": None if pbo_result is None else {
            "pbo": round(pbo_result["pbo"], 4),
            "oos_degradation": round(pbo_result["oos_degradation"], 4),
            "prob_oos_loss": round(pbo_result["prob_oos_loss"], 4),
            "n_configs": pbo_result["n_configs"],
            "logits": pbo_result["logits"],
        },
        "cost_curve": {
            "bps_grid": cost["bps_grid"],
            "net_sharpe": [round(s, 3) for s in cost["net_sharpe"]],
        },
        "red_flags": flags,
        "checklist": checklist,
        "notes": notes,
    }
