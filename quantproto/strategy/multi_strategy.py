"""Multi-strategy orchestration.

Runs multiple strategies, monitors correlations, allocates capital,
and implements kill switches.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quantproto.strategy.base import Strategy
from quantproto.analytics import DrawdownAnalytics


class MultiStrategyManager:
    """Manage portfolio of strategies.

    Features:
    - Strategy-level diversification
    - Return correlation monitoring
    - Dynamic capital allocation
    - Kill switch per strategy
    """

    def __init__(
        self,
        strategies: dict[str, Strategy],
        initial_allocation: dict[str, float] | None = None,
        kill_threshold: float = -0.15,
    ):
        self.strategies = strategies
        self.allocation = initial_allocation or {
            name: 1.0 / len(strategies) for name in strategies
        }
        self.kill_threshold = kill_threshold
        self.killed: set[str] = set()
        self.return_history: dict[str, list[float]] = {n: [] for n in strategies}

    def run_all(self, prices: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Run all active strategies, return signals dict."""
        signals = {}
        for name, strat in self.strategies.items():
            if name in self.killed:
                continue
            signals[name] = strat.generate_signal(prices)
        return signals

    def combine_signals(
        self,
        signals: dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """Combine strategy signals using current allocation weights."""
        combined = None
        total_weight = 0.0

        for name, sig in signals.items():
            if name in self.killed:
                continue
            weight = self.allocation.get(name, 0.0)
            if combined is None:
                combined = sig * weight
            else:
                common = combined.index.intersection(sig.index)
                combined = combined.loc[common] + sig.loc[common] * weight
            total_weight += weight

        if combined is not None and total_weight > 0:
            combined = combined / total_weight
        return combined

    def update_returns(self, strategy_returns: dict[str, float]) -> None:
        """Record per-strategy returns and check kill switches."""
        for name, ret in strategy_returns.items():
            self.return_history[name].append(ret)

            # Check kill switch
            if len(self.return_history[name]) >= 20:
                equity = np.cumprod(1 + np.array(self.return_history[name]))
                mdd = DrawdownAnalytics.max_drawdown(equity)
                if mdd < self.kill_threshold and name not in self.killed:
                    self.killed.add(name)

    def correlation_matrix(self) -> pd.DataFrame:
        """Compute correlation matrix of strategy returns."""
        data = {}
        for name, rets in self.return_history.items():
            if len(rets) > 0:
                data[name] = rets
        if not data:
            return pd.DataFrame()
        min_len = min(len(v) for v in data.values())
        trimmed = {k: v[:min_len] for k, v in data.items()}
        return pd.DataFrame(trimmed).corr()

    def rebalance(self, target: dict[str, float]) -> None:
        """Update allocation weights."""
        self.allocation = target

    def status(self) -> dict[str, Any]:
        """Current manager status."""
        return {
            "active": [n for n in self.strategies if n not in self.killed],
            "killed": list(self.killed),
            "allocation": self.allocation,
            "strategy_count": len(self.strategies),
        }
