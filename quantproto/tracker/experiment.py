"""Experiment — the user-facing tracker API.

    import quantproto as qp
    exp = qp.experiment("spy-meanrev")
    with exp.run(params={"lookback": 20}) as run:
        run.log_returns(daily_returns)
    exp.status()

Every logged run lands in the hash-chained ledger; the budget meter and the
full robustness report are recomputed from the accumulated history, so the
multiple-testing corrections always reflect the real search.
"""

from __future__ import annotations

import hashlib
import inspect
from typing import Any

import numpy as np

from quantproto.adapters.base import _coerce, _equity_series_to_returns
from quantproto.integrity.score import robustness_report
from quantproto.tracker.ledger import RunLedger
from quantproto.tracker.budget import (
    research_budget,
    parameter_sensitivity,
    _distinct_configs,
    _variant_matrix,
)
from quantproto.tracker.drift import live_consistency


def _code_hash(obj: Any) -> str | None:
    """sha256 of an object's source, when introspectable."""
    try:
        src = inspect.getsource(obj)
    except (TypeError, OSError):
        return None
    return hashlib.sha256(src.encode()).hexdigest()


class RunHandle:
    """One run in progress; log exactly one return series before exit."""

    def __init__(self, experiment: "Experiment", params: dict[str, Any],
                 source: str, code_hash: str | None):
        self._exp = experiment
        self._params = params
        self._source = source
        self._code_hash = code_hash
        self._returns: np.ndarray | None = None
        self.result: dict | None = None  # ledger receipt after exit

    def log_returns(self, returns) -> None:
        self._returns = _coerce(returns)

    def log_equity(self, equity) -> None:
        self._returns = _equity_series_to_returns(equity)

    def log_trades(self, pnl, capital: float) -> None:
        if capital <= 0:
            raise ValueError("capital must be positive")
        self._returns = np.asarray(list(pnl), dtype=float) / float(capital)

    def __enter__(self) -> "RunHandle":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            return False  # failed run: nothing to log, propagate
        if self._returns is None:
            raise RuntimeError(
                "Run exited without logging results — call log_returns(), "
                "log_equity() or log_trades() inside the `with` block."
            )
        self.result = self._exp._record(
            self._returns, self._params, self._source, self._code_hash
        )
        return False


class Experiment:
    """A named strategy search with a tamper-evident run history."""

    def __init__(self, name: str, ledger: RunLedger | None = None,
                 ledger_path: str | None = None):
        if not name or not name.strip():
            raise ValueError("experiment name must be non-empty")
        self.name = name.strip()
        self.ledger = ledger if ledger is not None else RunLedger(ledger_path)
        self.ledger.ensure_experiment(self.name)

    # ── Logging ───────────────────────────────────────────────────────────
    def run(self, params: dict[str, Any] | None = None, *, source: str = "manual",
            strategy=None) -> RunHandle:
        """Open a run context; ``strategy`` (fn/class) is hashed for provenance."""
        return RunHandle(self, dict(params or {}), source, _code_hash(strategy))

    def log(self, returns, params: dict[str, Any] | None = None, *,
            source: str = "manual", strategy=None) -> dict:
        """One-liner: log a completed run's return series."""
        return self._record(_coerce(returns), dict(params or {}), source,
                            _code_hash(strategy))

    def log_live(self, returns, params: dict[str, Any] | None = None) -> dict:
        """Log live fills (returns or per-period P&L fractions) for drift tracking.

        Kept out of the research-budget's config search (see
        :func:`quantproto.tracker.budget._distinct_configs`) — this is the
        deployed strategy's real track record, not a new variant.
        """
        return self._record(_coerce(returns), dict(params or {}), "live", None)

    def _record(self, returns: np.ndarray, params: dict, source: str,
                code_hash: str | None) -> dict:
        return self.ledger.record_run(
            self.name, returns, params, source=source, code_hash=code_hash
        )

    # ── Framework capture ─────────────────────────────────────────────────
    def capture_backtesting(self, bt, **run_kwargs) -> Any:
        """Run a `backtesting.py` Backtest and log it; returns its stats.

        ``run_kwargs`` are forwarded to ``bt.run()`` and recorded as the run's
        params (they are the knobs being searched).
        """
        stats = bt.run(**run_kwargs)
        equity = stats["_equity_curve"]["Equity"]
        strategy = getattr(bt, "_strategy", None)
        run = self.run(params=run_kwargs, source="backtesting", strategy=strategy)
        with run:
            run.log_equity(equity)
        return stats

    def capture_vectorbt(self, portfolio, params: dict[str, Any] | None = None) -> dict:
        """Log a vectorbt Portfolio's returns; returns the ledger receipt."""
        returns = portfolio.returns()
        return self.log(returns, params=params, source="vectorbt")

    def capture_zipline(self, perf, params: dict[str, Any] | None = None) -> dict:
        """Log a Zipline ``run_algorithm()`` perf DataFrame; returns the receipt.

        Reuses the same extraction as :func:`quantproto.adapters.zipline.audit_zipline`.
        """
        from quantproto.adapters.zipline import _extract

        returns_arr, _ = _extract(perf)
        return self.log(returns_arr, params=params, source="zipline")

    def capture_bt(self, result, strategy_name: str | None = None,
                   params: dict[str, Any] | None = None) -> dict:
        """Log a ``bt.Result`` object; returns the receipt.

        Reuses the same extraction as :func:`quantproto.adapters.bt.audit_bt`.
        """
        from quantproto.adapters.bt import _extract

        returns_arr, _ = _extract(result, strategy_name)
        return self.log(returns_arr, params=params, source="bt")

    # ── Analysis ──────────────────────────────────────────────────────────
    def _runs(self) -> list[dict]:
        return self.ledger.list_runs(self.name, with_returns=True)

    def status(self) -> dict:
        """Research-budget meter over the full logged search."""
        return research_budget(self._runs())

    def report(self, turnover: float = 1.0, n_splits: int = 16) -> dict:
        """Full robustness report of the best config, variant matrix auto-built."""
        runs = self._runs()
        if not runs:
            raise ValueError(f"experiment '{self.name}' has no logged runs")
        configs = _distinct_configs(runs)
        best = max(configs, key=lambda c: c["sharpe"])
        vm = _variant_matrix(configs, n_splits)
        rep = robustness_report(
            np.asarray(best["returns"], dtype=float),
            n_trials=len(configs),
            turnover=turnover,
            variant_matrix=vm,
            n_splits=n_splits,
        )
        rep["experiment"] = {
            "name": self.name,
            "n_runs": len(runs),
            "n_configs": len(configs),
            "best_params": best["params"],
            "chain_valid": self.ledger.verify_chain(self.name),
        }
        return rep

    def sensitivity(self, param: str) -> dict:
        return parameter_sensitivity(self._runs(), param)

    def drift(self, target_prob: float = 0.95) -> dict:
        """Live-vs-backtest consistency: has the deployed edge decayed?

        Compares all logged live fills against the best backtest config's
        returns. Requires at least one backtest run and ``MIN_LIVE_OBS`` live
        observations.
        """
        runs = self._runs()
        configs = _distinct_configs(runs)
        if not configs:
            return {"state": "no_backtest", "message":
                    f"experiment '{self.name}' has no logged backtest runs to compare against."}
        live_runs = [r for r in runs if r["source"] == "live"]
        if not live_runs:
            return {"state": "no_live_data", "message":
                    "No live fills logged yet — call exp.log_live() as fills come in."}

        best = max(configs, key=lambda c: c["sharpe"])
        live_returns = np.concatenate([r["returns"] for r in live_runs])
        return live_consistency(
            np.asarray(best["returns"], dtype=float), live_returns, target_prob=target_prob
        )

    def runs(self) -> list[dict]:
        """Run history without the raw return arrays."""
        return self.ledger.list_runs(self.name, with_returns=False)

    def verify(self) -> bool:
        return self.ledger.verify_chain(self.name)


def experiment(name: str, ledger_path: str | None = None) -> Experiment:
    """Open (or create) a tracked experiment."""
    return Experiment(name, ledger_path=ledger_path)
