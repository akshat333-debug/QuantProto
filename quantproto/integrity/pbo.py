"""Probability of Backtest Overfitting (PBO) via CSCV.

Combinatorially Symmetric Cross-Validation (Bailey, Borwein, López de Prado,
Zhu, 2017). Given a matrix of returns for *many* strategy configurations,
PBO estimates the probability that the configuration which looks best
in-sample (IS) underperforms the median out-of-sample (OOS) — i.e. that your
"winner" was selected by overfitting rather than skill.

Input is a ``(T, N)`` matrix: T time observations, N strategy configurations.

The procedure:
  1. Split the T rows into S equal blocks.
  2. For every way of choosing S/2 blocks as IS (the rest are OOS):
     - rank configs by IS performance, take the IS-best,
     - find that config's *relative rank* ω in OOS,
     - logit λ = ln(ω / (1 − ω)).
  3. PBO = fraction of splits with λ < 0 (IS-best lands below OOS median).

A PBO near 0 means the selection process generalises; near 1 means the
backtest is almost certainly overfit.
"""

from __future__ import annotations

import itertools

import numpy as np


def _block_moments(matrix: np.ndarray, n_splits: int):
    """Pre-aggregate per-block sum / sum-of-squares / count per strategy.

    Lets us compute the Sharpe of any union of blocks in O(blocks) instead
    of re-scanning the raw rows for each of the C(S, S/2) combinations.
    """
    T, N = matrix.shape
    block_size = T // n_splits
    usable = block_size * n_splits
    m = matrix[:usable]
    blocks = m.reshape(n_splits, block_size, N)
    bsum = blocks.sum(axis=1)            # (S, N)
    bsq = (blocks**2).sum(axis=1)        # (S, N)
    bcount = np.full(n_splits, block_size)
    return bsum, bsq, bcount


def _sharpe_from_moments(sum_, sq_, count_):
    """Population Sharpe (mean/std, ddof=0) from aggregated moments."""
    mean = sum_ / count_
    var = sq_ / count_ - mean**2
    var = np.clip(var, 1e-24, None)
    return mean / np.sqrt(var)


def pbo_cscv(
    perf_matrix: np.ndarray,
    n_splits: int = 16,
) -> dict:
    """Compute the Probability of Backtest Overfitting.

    Parameters
    ----------
    perf_matrix : array of shape (T, N) — returns of N strategy configs over
        T observations. N must be ≥ 2 (PBO compares configs against each other).
    n_splits : number of blocks S (even). C(S, S/2) combinations are evaluated.

    Returns
    -------
    {
        "pbo": float,                 # P(overfit) in [0, 1]
        "logits": [float],           # logit distribution across splits
        "oos_degradation": float,    # mean IS Sharpe − mean OOS Sharpe of winner
        "prob_oos_loss": float,      # P(winner has negative OOS Sharpe)
        "n_configs": int,
        "n_combinations": int,
    }
    """
    M = np.asarray(perf_matrix, dtype=float)
    if M.ndim != 2:
        raise ValueError(f"perf_matrix must be 2D (T, N); got shape {M.shape}")
    T, N = M.shape
    if N < 2:
        raise ValueError(
            f"PBO needs ≥ 2 strategy configurations to compare; got {N}. "
            "For a single series, use the deflated Sharpe / cost-sensitivity "
            "diagnostics instead."
        )
    if n_splits % 2 != 0:
        raise ValueError(f"n_splits must be even; got {n_splits}")
    if n_splits > T:
        raise ValueError(f"n_splits ({n_splits}) cannot exceed T ({T})")

    bsum, bsq, bcount = _block_moments(M, n_splits)
    block_ids = list(range(n_splits))
    half = n_splits // 2

    logits: list[float] = []
    is_sharpes_winner: list[float] = []
    oos_sharpes_winner: list[float] = []

    for is_blocks in itertools.combinations(block_ids, half):
        is_set = list(is_blocks)
        oos_set = [b for b in block_ids if b not in is_blocks]

        is_sum = bsum[is_set].sum(axis=0)
        is_sq = bsq[is_set].sum(axis=0)
        is_n = bcount[is_set].sum()
        oos_sum = bsum[oos_set].sum(axis=0)
        oos_sq = bsq[oos_set].sum(axis=0)
        oos_n = bcount[oos_set].sum()

        is_sharpe = _sharpe_from_moments(is_sum, is_sq, is_n)
        oos_sharpe = _sharpe_from_moments(oos_sum, oos_sq, oos_n)

        winner = int(np.argmax(is_sharpe))

        # Relative rank of the IS-winner among OOS performances, in (0, 1).
        # rank = #configs the winner beats OOS; ω = rank / (N + 1).
        oos_rank = float(np.sum(oos_sharpe <= oos_sharpe[winner]))
        omega = oos_rank / (N + 1.0)
        omega = min(max(omega, 1e-6), 1.0 - 1e-6)
        logits.append(float(np.log(omega / (1.0 - omega))))

        is_sharpes_winner.append(float(is_sharpe[winner]))
        oos_sharpes_winner.append(float(oos_sharpe[winner]))

    logits_arr = np.array(logits)
    pbo = float(np.mean(logits_arr < 0.0))
    oos_deg = float(np.mean(is_sharpes_winner) - np.mean(oos_sharpes_winner))
    prob_oos_loss = float(np.mean(np.array(oos_sharpes_winner) < 0.0))

    return {
        "pbo": pbo,
        "logits": logits,
        "oos_degradation": oos_deg,
        "prob_oos_loss": prob_oos_loss,
        "n_configs": N,
        "n_combinations": len(logits),
    }
