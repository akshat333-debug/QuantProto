"""Drawdown and tail-risk analytics."""

from __future__ import annotations

import numpy as np
import pandas as pd


class DrawdownAnalytics:
    """Drawdown, underwater curve, and related risk metrics."""

    @staticmethod
    def drawdown_series(equity_curve: pd.Series | np.ndarray) -> pd.Series | np.ndarray:
        """Compute drawdown at each point (always ≤ 0)."""
        eq = np.asarray(equity_curve)
        running_max = np.maximum.accumulate(eq)
        dd = eq / running_max - 1.0
        if isinstance(equity_curve, pd.Series):
            return pd.Series(dd, index=equity_curve.index, name="drawdown")
        return dd

    @staticmethod
    def max_drawdown(equity_curve: pd.Series | np.ndarray) -> float:
        """Maximum drawdown (most negative value)."""
        dd = DrawdownAnalytics.drawdown_series(equity_curve)
        return float(np.min(dd))

    @staticmethod
    def calmar_ratio(
        returns: np.ndarray | pd.Series,
        equity_curve: pd.Series | np.ndarray | None = None,
        periods_per_year: int = 252,
    ) -> float:
        """Calmar ratio: annualised return / |max drawdown|."""
        r = np.asarray(returns)
        ann_return = np.mean(r) * periods_per_year
        if equity_curve is None:
            equity_curve = np.cumprod(1 + r)
        mdd = DrawdownAnalytics.max_drawdown(equity_curve)
        if abs(mdd) < 1e-12:
            return 0.0
        return float(ann_return / abs(mdd))

    @staticmethod
    def pain_index(equity_curve: pd.Series | np.ndarray) -> float:
        """Pain index: mean of absolute drawdowns."""
        dd = DrawdownAnalytics.drawdown_series(equity_curve)
        return float(np.mean(np.abs(dd)))

    @staticmethod
    def underwater_periods(equity_curve: pd.Series | np.ndarray) -> list[dict]:
        """Identify drawdown periods with start, trough, end, depth, duration."""
        dd = np.asarray(DrawdownAnalytics.drawdown_series(equity_curve))
        periods = []
        in_dd = False
        start = 0
        trough = 0
        trough_val = 0.0

        for i in range(len(dd)):
            if dd[i] < -1e-10 and not in_dd:
                in_dd = True
                start = i
                trough = i
                trough_val = dd[i]
            elif in_dd and dd[i] < trough_val:
                trough = i
                trough_val = dd[i]
            elif in_dd and dd[i] >= -1e-10:
                periods.append({
                    "start": start,
                    "trough": trough,
                    "end": i,
                    "depth": float(trough_val),
                    "duration": i - start,
                })
                in_dd = False

        if in_dd:
            periods.append({
                "start": start,
                "trough": trough,
                "end": len(dd) - 1,
                "depth": float(trough_val),
                "duration": len(dd) - start,
            })
        return periods

    @staticmethod
    def drawdown_position_scale(
        equity_curve: pd.Series | np.ndarray,
        max_dd_threshold: float = -0.10,
        min_scale: float = 0.3,
    ) -> np.ndarray:
        """Scale positions based on current drawdown depth.

        In deep drawdown → reduce exposure. Recovering → increase.
        """
        dd = np.asarray(DrawdownAnalytics.drawdown_series(equity_curve))
        scales = np.ones_like(dd)
        for i in range(len(dd)):
            if dd[i] < max_dd_threshold:
                # Linear scale from 1.0 at threshold to min_scale at 2x threshold
                depth_ratio = min(abs(dd[i] / max_dd_threshold), 2.0)
                scales[i] = max(min_scale, 1.0 - (depth_ratio - 1.0) * (1.0 - min_scale))
            elif dd[i] < 0:
                scales[i] = 1.0
        return scales
