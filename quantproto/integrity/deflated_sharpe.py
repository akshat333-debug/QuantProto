"""Deflated & Probabilistic Sharpe Ratio (Bailey & López de Prado).

These statistics correct the Sharpe ratio for the three things that make
backtested Sharpes lie:

1. **Sample length** — a high Sharpe over 30 days means little.
2. **Non-normality** — negative skew and fat tails inflate naive Sharpe.
3. **Selection bias / multiple testing** — if you tried 100 strategy
   variants and kept the best, its Sharpe is biased upward.

References
----------
- Bailey, López de Prado (2012). "The Sharpe Ratio Efficient Frontier"
  (Probabilistic Sharpe Ratio, Minimum Track Record Length).
- Bailey, López de Prado (2014). "The Deflated Sharpe Ratio: Correcting
  for Selection Bias, Backtest Overfitting and Non-Normality."

All Sharpe ratios in this module are **per-observation** (not annualised) —
the statistics depend on the raw return distribution and sample size.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm, skew as _skew, kurtosis as _kurtosis

EULER_MASCHERONI = 0.5772156649015329


def _sample_stats(returns: np.ndarray) -> tuple[float, float, float, int]:
    """Return (per-period Sharpe, skewness, Pearson kurtosis, n)."""
    r = np.asarray(returns, dtype=float)
    n = r.size
    std = np.std(r, ddof=1)
    sr = 0.0 if std < 1e-12 else float(np.mean(r) / std)
    g3 = float(_skew(r, bias=False)) if n > 2 else 0.0
    # Pearson kurtosis (normal == 3), not excess.
    g4 = float(_kurtosis(r, fisher=False, bias=False)) if n > 3 else 3.0
    return sr, g3, g4, n


def probabilistic_sharpe_ratio(
    sharpe: float,
    n: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
    sharpe_benchmark: float = 0.0,
) -> float:
    """Probability that the *true* Sharpe exceeds ``sharpe_benchmark``.

    PSR(SR*) = Φ[ (SR − SR*)·√(n−1) / √(1 − γ3·SR + (γ4−1)/4·SR²) ]

    Parameters
    ----------
    sharpe : observed per-period Sharpe ratio.
    n : number of return observations.
    skew : sample skewness (γ3).
    kurtosis : sample Pearson kurtosis (γ4, normal = 3).
    sharpe_benchmark : threshold Sharpe (SR*), per-period.

    Returns
    -------
    Probability in [0, 1].
    """
    if n < 2:
        return 0.0
    denom = 1.0 - skew * sharpe + (kurtosis - 1.0) / 4.0 * sharpe**2
    # Numerical guard: the variance term must be positive.
    denom = max(denom, 1e-12)
    z = (sharpe - sharpe_benchmark) * np.sqrt(n - 1) / np.sqrt(denom)
    return float(norm.cdf(z))


def expected_max_sharpe(n_trials: int, var_sharpe: float) -> float:
    """Expected maximum Sharpe from ``n_trials`` independent trials.

    E[max SR] ≈ √Var(SR) · [(1−γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e))]

    where γ is the Euler–Mascheroni constant. This is the benchmark a
    strategy must beat to be considered non-spurious after a search over
    ``n_trials`` configurations.

    Parameters
    ----------
    n_trials : number of independent strategy configurations tried.
    var_sharpe : variance of the per-period Sharpe ratios across trials.

    Returns
    -------
    Expected maximum per-period Sharpe (0.0 when n_trials ≤ 1).
    """
    if n_trials <= 1 or var_sharpe <= 0:
        return 0.0
    sqrt_var = np.sqrt(var_sharpe)
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(sqrt_var * ((1.0 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2))


def deflated_sharpe_ratio(
    sharpe: float,
    n: int,
    n_trials: int,
    var_sharpe: float,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> dict[str, float]:
    """Deflated Sharpe Ratio — PSR against the multiple-testing benchmark.

    DSR = PSR(SR*) where SR* = E[max SR over n_trials]. A low DSR means
    the observed Sharpe is plausibly the product of luck across many trials.

    Returns
    -------
    {"dsr": prob, "expected_max_sharpe": SR*, "psr_vs_zero": PSR(0)}
    """
    sr_benchmark = expected_max_sharpe(n_trials, var_sharpe)
    dsr = probabilistic_sharpe_ratio(sharpe, n, skew, kurtosis, sr_benchmark)
    psr0 = probabilistic_sharpe_ratio(sharpe, n, skew, kurtosis, 0.0)
    return {
        "dsr": dsr,
        "expected_max_sharpe": sr_benchmark,
        "psr_vs_zero": psr0,
    }


def minimum_track_record_length(
    sharpe: float,
    skew: float = 0.0,
    kurtosis: float = 3.0,
    sharpe_benchmark: float = 0.0,
    target_prob: float = 0.95,
) -> float:
    """Minimum observations needed for PSR(SR*) ≥ ``target_prob``.

    MinTRL = 1 + (1 − γ3·SR + (γ4−1)/4·SR²) · (Z_target / (SR − SR*))²

    Returns ``inf`` when the observed Sharpe does not exceed the benchmark
    (no track record length can make a non-edge significant).
    """
    if sharpe <= sharpe_benchmark:
        return float("inf")
    z = norm.ppf(target_prob)
    var_term = 1.0 - skew * sharpe + (kurtosis - 1.0) / 4.0 * sharpe**2
    var_term = max(var_term, 1e-12)
    return float(1.0 + var_term * (z / (sharpe - sharpe_benchmark)) ** 2)


def analyze_returns(
    returns: np.ndarray,
    n_trials: int = 1,
    var_sharpe: float | None = None,
    target_prob: float = 0.95,
) -> dict[str, float]:
    """Convenience wrapper: compute all DSR/PSR statistics from a return series.

    When ``var_sharpe`` is unknown and ``n_trials`` > 1, the deflation term
    cannot be computed and ``dsr`` is returned as ``None``.
    """
    sr, g3, g4, n = _sample_stats(returns)
    psr = probabilistic_sharpe_ratio(sr, n, g3, g4, 0.0)
    min_trl = minimum_track_record_length(sr, g3, g4, 0.0, target_prob)
    out: dict[str, float] = {
        "sharpe_per_period": sr,
        "sharpe_annualized": sr * np.sqrt(252),
        "skew": g3,
        "kurtosis": g4,
        "n_obs": n,
        "psr": psr,
        "min_track_record_length": min_trl,
        "n_trials": n_trials,
    }
    if n_trials > 1 and var_sharpe is not None:
        dsr_res = deflated_sharpe_ratio(sr, n, n_trials, var_sharpe, g3, g4)
        out["dsr"] = dsr_res["dsr"]
        out["expected_max_sharpe"] = dsr_res["expected_max_sharpe"]
    else:
        out["dsr"] = None
        out["expected_max_sharpe"] = 0.0
    return out
