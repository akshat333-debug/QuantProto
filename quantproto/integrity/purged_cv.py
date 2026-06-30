"""Purged & embargoed K-fold cross-validation for time series.

Standard K-fold leaks information in financial data: a test block sitting in
the middle of the series shares serially-correlated neighbours with the
training set, so the model effectively sees adjacent information. López de
Prado's purged K-fold removes (`purges`) training observations immediately
around each test block and applies an `embargo` after it.

This splitter yields leak-free (train_idx, test_idx) pairs that the
orchestrator and the bring-your-own-backtest auditor use for honest
out-of-sample validation.
"""

from __future__ import annotations

import numpy as np


class PurgedKFold:
    """K-fold splitter with purge gap and post-test embargo.

    Parameters
    ----------
    n_splits : number of folds.
    purge : observations removed from training on each side of the test block.
    embargo_pct : fraction of total observations embargoed after the test block.
    """

    def __init__(self, n_splits: int = 5, purge: int = 1, embargo_pct: float = 0.01):
        if n_splits < 2:
            raise ValueError(f"n_splits must be ≥ 2; got {n_splits}")
        if purge < 0:
            raise ValueError(f"purge must be ≥ 0; got {purge}")
        if not 0.0 <= embargo_pct < 1.0:
            raise ValueError(f"embargo_pct must be in [0, 1); got {embargo_pct}")
        self.n_splits = n_splits
        self.purge = purge
        self.embargo_pct = embargo_pct

    def split(self, n_samples: int):
        """Yield (train_idx, test_idx) arrays for each fold.

        Test folds are contiguous blocks covering the series in order.
        """
        if n_samples < self.n_splits:
            raise ValueError(
                f"n_samples ({n_samples}) must be ≥ n_splits ({self.n_splits})"
            )
        indices = np.arange(n_samples)
        embargo = int(n_samples * self.embargo_pct)
        fold_bounds = np.array_split(indices, self.n_splits)

        for fold in fold_bounds:
            test_start, test_end = fold[0], fold[-1]
            test_idx = indices[test_start : test_end + 1]

            # Purge a buffer on both sides + embargo after the test block.
            left = test_start - self.purge
            right = test_end + self.purge + embargo
            train_mask = (indices < left) | (indices > right)
            train_idx = indices[train_mask]
            yield train_idx, test_idx
