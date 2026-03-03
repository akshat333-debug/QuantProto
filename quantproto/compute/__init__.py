"""Distributed computing — async task definitions.

Uses concurrent.futures for local parallelism.
Designed to be swappable with Celery for production.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable

import numpy as np
import pandas as pd

from quantproto.walk_forward import WalkForwardBacktester
from quantproto.risk_engine import RiskEngine


def _run_single_backtest(args: dict) -> dict[str, Any]:
    """Worker function for parallel backtesting."""
    prices = pd.DataFrame(args["prices"])
    train_window = args["train_window"]
    test_window = args["test_window"]
    strategy_name = args["strategy_name"]

    def equal_weight_signal(train_prices):
        n = train_prices.shape[1]
        return pd.DataFrame(
            np.ones_like(train_prices.values) / n,
            index=train_prices.index,
            columns=train_prices.columns,
        )

    result = WalkForwardBacktester.run(prices, equal_weight_signal, train_window, test_window)
    sharpe = RiskEngine.sharpe_ratio(result["returns"].values)

    return {
        "strategy": strategy_name,
        "sharpe": sharpe,
        "n_splits": result["n_splits"],
        "total_return": float(result["equity_curve"].iloc[-1] - 1),
    }


class ParallelBacktester:
    """Run multiple backtests in parallel using ProcessPoolExecutor."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def run_parallel(
        self, tasks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Run backtests in parallel.

        Parameters
        ----------
        tasks : list of dicts with {prices, train_window, test_window, strategy_name}

        Returns
        -------
        List of result dicts.
        """
        results = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(_run_single_backtest, task): task["strategy_name"]
                for task in tasks
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "strategy": futures[future],
                        "error": str(e),
                    })
        return results


class AsyncTaskQueue:
    """Simple async task queue for compute-heavy operations.

    This is a thin wrapper around concurrent.futures designed to be
    swapped with Celery/Redis in production Docker deployment.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._results: dict[str, Any] = {}

    def submit(
        self, task_id: str, fn: Callable, *args: Any, **kwargs: Any
    ) -> str:
        """Submit a task and return its ID."""
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn, *args, **kwargs)
            self._results[task_id] = future.result()
        return task_id

    def get_result(self, task_id: str) -> Any:
        """Get result by task ID."""
        if task_id not in self._results:
            raise KeyError(f"Task {task_id} not found")
        return self._results[task_id]

    @property
    def completed_tasks(self) -> list[str]:
        return list(self._results.keys())
