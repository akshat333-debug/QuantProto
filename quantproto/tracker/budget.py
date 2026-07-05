"""Research-budget engine — the honest overfitting math over a run ledger.

Every statistic here is computed from the *observed* search history (the runs
actually logged), never from a self-reported trial count. This is the core of
the tracker pivot: DSR/PBO inputs that used to be guesses become measurements.
"""

from __future__ import annotations

import numpy as np

from quantproto.integrity.deflated_sharpe import analyze_returns, expected_max_sharpe
from quantproto.integrity.pbo import pbo_cscv

ANNUALIZE = float(np.sqrt(252))

# PBO needs enough configs to rank against each other and enough observations
# to split into CSCV blocks.
PBO_MIN_CONFIGS = 8
PBO_MIN_OBS_PER_SPLIT = 4


def _distinct_configs(runs: list[dict]) -> list[dict]:
    """Latest run per params_hash (re-running one config mines no new noise)."""
    by_hash: dict[str, dict] = {}
    for r in runs:  # runs are ordered by seq ascending
        by_hash[r["params_hash"]] = r
    return list(by_hash.values())


def _variant_matrix(configs: list[dict], n_splits: int) -> np.ndarray | None:
    """(T_min, N) matrix of each config's most recent returns, tail-aligned."""
    if len(configs) < PBO_MIN_CONFIGS:
        return None
    t_min = min(int(c["n_obs"]) for c in configs)
    if t_min < n_splits * PBO_MIN_OBS_PER_SPLIT:
        return None
    cols = [np.asarray(c["returns"], dtype=float)[-t_min:] for c in configs]
    return np.column_stack(cols)


def research_budget(runs: list[dict], n_splits: int = 16) -> dict:
    """Compute the budget meter from logged runs (need ``returns`` on each).

    Returns a dict with the honest N, best/spurious/haircut Sharpe (annualized),
    DSR, PBO when available, a state flag and a plain-English message.
    """
    if not runs:
        return {
            "n_runs": 0,
            "n_configs": 0,
            "budget_state": "empty",
            "message": "No runs logged yet.",
        }

    configs = _distinct_configs(runs)
    n_trials = len(configs)
    sharpes = np.array([float(c["sharpe"]) for c in configs])
    best_idx = int(np.argmax(sharpes))
    best = configs[best_idx]
    best_returns = np.asarray(best["returns"], dtype=float)

    var_sharpe = float(np.var(sharpes, ddof=1)) if n_trials > 1 else 0.0

    # Expected max per-period Sharpe under the search. When all runs happen to
    # produce identical Sharpe (var 0), fall back to the pure-noise null
    # E[max SR] ≈ √(2·ln N / T): N draws of an SR estimator with variance 1/T.
    if n_trials > 1 and var_sharpe > 0:
        spurious_pp = expected_max_sharpe(n_trials, var_sharpe)
    elif n_trials > 1:
        spurious_pp = float(np.sqrt(2.0 * np.log(n_trials) / best_returns.size))
    else:
        spurious_pp = 0.0

    stats = analyze_returns(
        best_returns,
        n_trials=n_trials,
        var_sharpe=var_sharpe if var_sharpe > 0 else None,
    )

    # PBO across the tail-aligned variant matrix.
    pbo_summary = None
    vm = _variant_matrix(configs, n_splits)
    if vm is not None:
        splits = n_splits if vm.shape[0] >= n_splits * PBO_MIN_OBS_PER_SPLIT else 8
        res = pbo_cscv(vm, n_splits=splits)
        pbo_summary = {
            "pbo": round(res["pbo"], 4),
            "oos_degradation": round(res["oos_degradation"], 4),
            "prob_oos_loss": round(res["prob_oos_loss"], 4),
            "n_configs": res["n_configs"],
        }

    best_ann = float(sharpes[best_idx]) * ANNUALIZE
    spurious_ann = spurious_pp * ANNUALIZE
    haircut_ann = best_ann - spurious_ann
    dsr = stats["dsr"]
    pbo_val = pbo_summary["pbo"] if pbo_summary else None

    # ── State + message ───────────────────────────────────────────────────
    if n_trials == 1:
        state = "ok"
        message = (
            "1 config logged. The budget meter starts mattering once you iterate — "
            "keep logging every variant."
        )
    elif best_ann <= spurious_ann or (dsr is not None and dsr < 0.5):
        state = "burned"
        message = (
            f"{n_trials} configs tried — pure noise would already produce an annualized "
            f"Sharpe of {spurious_ann:.2f}. Your best is {best_ann:.2f}: indistinguishable "
            "from luck. Keep the dataset, change the thesis."
        )
    elif (dsr is not None and dsr < 0.95) or (pbo_val is not None and pbo_val > 0.5):
        state = "warning"
        message = (
            f"{n_trials} configs tried; best annualized Sharpe {best_ann:.2f} vs "
            f"{spurious_ann:.2f} expected from noise. Edge not yet significant after "
            "deflation — more out-of-sample data beats more tweaking."
        )
    else:
        state = "ok"
        message = (
            f"Best annualized Sharpe {best_ann:.2f} survives deflation for "
            f"{n_trials} trials (noise benchmark {spurious_ann:.2f})."
        )

    return {
        "n_runs": len(runs),
        "n_configs": n_trials,
        "best_run_id": best["id"],
        "best_params": best["params"],
        "best_sharpe_ann": round(best_ann, 3),
        "spurious_sharpe_ann": round(spurious_ann, 3),
        "haircut_sharpe_ann": round(haircut_ann, 3),
        "psr": round(stats["psr"], 4),
        "dsr": None if dsr is None else round(dsr, 4),
        "var_sharpe": round(var_sharpe, 8),
        "pbo": pbo_summary,
        "n_obs_best": int(best_returns.size),
        "budget_state": state,
        "message": message,
    }


def parameter_sensitivity(runs: list[dict], param: str) -> dict:
    """Sharpe as a function of one parameter — the 'RSI 13/14/15' test.

    Groups distinct configs by ``param``'s value (best Sharpe per value),
    sorts numerically when possible, and reports how much the best value's
    neighbours degrade. A sharp peak (low ``neighbour_ratio``) is the classic
    overfit signature; a plateau is what a real effect looks like.
    """
    configs = _distinct_configs(runs)
    by_value: dict[object, float] = {}
    for c in configs:
        if param not in c["params"]:
            continue
        v = c["params"][param]
        s = float(c["sharpe"])
        if v not in by_value or s > by_value[v]:
            by_value[v] = s

    if len(by_value) < 3:
        return {
            "param": param,
            "n_values": len(by_value),
            "values": sorted(by_value.keys(), key=str),
            "verdict": "insufficient",
            "message": f"Need ≥ 3 distinct values of '{param}' to assess sensitivity; "
                       f"have {len(by_value)}.",
        }

    try:
        items = sorted(by_value.items(), key=lambda kv: float(kv[0]))
        numeric = True
    except (TypeError, ValueError):
        items = sorted(by_value.items(), key=lambda kv: str(kv[0]))
        numeric = False

    values = [v for v, _ in items]
    sharpes = [s * ANNUALIZE for _, s in items]
    peak_idx = int(np.argmax(sharpes))
    peak = sharpes[peak_idx]

    neighbours = [
        sharpes[i] for i in (peak_idx - 1, peak_idx + 1) if 0 <= i < len(sharpes)
    ]
    if peak <= 0 or not numeric:
        ratio = None
        verdict = "inconclusive"
        message = "Peak Sharpe non-positive or values non-numeric; ratio not meaningful."
    else:
        ratio = max(min(max(neighbours) / peak, 1.0), -1.0) if neighbours else None
        if ratio is None:
            verdict = "inconclusive"
            message = "Peak is at the edge of the tested range with no neighbour."
        elif ratio >= 0.7:
            verdict = "plateau"
            message = (
                f"Neighbouring values of '{param}' retain {ratio:.0%} of peak Sharpe — "
                "consistent with a real effect."
            )
        elif ratio >= 0.3:
            verdict = "soft_peak"
            message = (
                f"Neighbours retain only {ratio:.0%} of peak Sharpe — treat "
                f"'{param}={values[peak_idx]}' with suspicion."
            )
        else:
            verdict = "sharp_peak"
            message = (
                f"Sharpe collapses away from '{param}={values[peak_idx]}' "
                f"({ratio:.0%} retained). Classic overfit signature."
            )

    return {
        "param": param,
        "n_values": len(values),
        "values": values,
        "sharpe_ann_by_value": [round(s, 3) for s in sharpes],
        "peak_value": values[peak_idx],
        "neighbour_ratio": None if ratio is None else round(ratio, 3),
        "verdict": verdict,
        "message": message,
    }
