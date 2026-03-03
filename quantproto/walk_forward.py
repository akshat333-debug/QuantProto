"""Walk-forward backtester with no-lookahead enforcement and bootstrap CI.

Implements rolling train/test splits, generates equity curves,
and computes bootstrap confidence intervals on the Sharpe ratio.
All operations are deterministically seeded.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd


class WalkForwardBacktester:
    """Rolling walk-forward engine with bootstrap statistics."""

    # ------------------------------------------------------------------
    # Window splitting
    # ------------------------------------------------------------------

    @staticmethod
    def _split_windows(
        n: int,
        train_window: int,
        test_window: int,
    ) -> list[tuple[int, int, int, int]]:
        """Generate non-overlapping (train, test) index ranges.

        Parameters
        ----------
        n : total number of observations.
        train_window : number of observations in training set.
        test_window : number of observations in test set.

        Returns
        -------
        List of (train_start, train_end, test_start, test_end) tuples.
        End indices are exclusive (Python-style slicing).

        Raises
        ------
        ValueError : if windows exceed total observations.
        """
        if train_window + test_window > n:
            raise ValueError(
                f"train_window ({train_window}) + test_window ({test_window}) "
                f"> n ({n})"
            )

        splits = []
        start = 0
        while start + train_window + test_window <= n:
            train_start = start
            train_end = start + train_window
            test_start = train_end
            test_end = test_start + test_window
            splits.append((train_start, train_end, test_start, test_end))
            start += test_window  # roll forward by one test window

        return splits

    # ------------------------------------------------------------------
    # Main backtest loop
    # ------------------------------------------------------------------

    @staticmethod
    def run(
        prices: pd.DataFrame,
        signal_fn: Callable[[pd.DataFrame], pd.DataFrame],
        train_window: int = 60,
        test_window: int = 20,
    ) -> dict:
        """Execute walk-forward backtest.

        Parameters
        ----------
        prices : DataFrame of close prices (index=dates, cols=tickers).
        signal_fn : function(train_prices) → signal DataFrame aligned to
            train_prices index, values in [0,1]. Only the last row is used
            to generate positions for the test period.
        train_window : number of periods in each training window.
        test_window : number of periods in each test window.

        Returns
        -------
        {
            "returns": pd.Series of portfolio returns across all test windows,
            "equity_curve": pd.Series starting at 1.0,
            "n_splits": int,
            "splits": list of split tuples,
        }
        """
        returns = prices.pct_change().dropna()
        n = len(returns)
        splits = WalkForwardBacktester._split_windows(n, train_window, test_window)

        all_test_returns: list[float] = []
        test_dates: list = []

        for train_start, train_end, test_start, test_end in splits:
            # Train: generate signal (no future data)
            train_prices = prices.iloc[train_start:train_end]
            signal = signal_fn(train_prices)

            # Use last row of signal as position weights for test period
            if isinstance(signal, pd.DataFrame):
                weights = signal.iloc[-1].values
            else:
                weights = np.array([signal.iloc[-1]])

            # Normalise weights to sum to 1
            weight_sum = np.sum(np.abs(weights))
            if weight_sum > 0:
                weights = weights / weight_sum

            # Test: compute portfolio return for each test day
            test_rets = returns.iloc[test_start:test_end]
            for idx in range(len(test_rets)):
                daily_port_ret = float(np.dot(weights, test_rets.iloc[idx].values))
                all_test_returns.append(daily_port_ret)
                test_dates.append(test_rets.index[idx])

        port_returns = pd.Series(all_test_returns, index=test_dates, name="portfolio")
        eq_curve = WalkForwardBacktester.equity_curve(port_returns)

        return {
            "returns": port_returns,
            "equity_curve": eq_curve,
            "n_splits": len(splits),
            "splits": splits,
        }

    # ------------------------------------------------------------------
    # Equity curve
    # ------------------------------------------------------------------

    @staticmethod
    def equity_curve(returns: pd.Series | np.ndarray) -> pd.Series | np.ndarray:
        """Cumulative wealth index starting at 1.0.

        Parameters
        ----------
        returns : periodic return series.

        Returns
        -------
        Same type as input, starting at 1.0.
        """
        if isinstance(returns, pd.Series):
            return (1 + returns).cumprod()
        return np.cumprod(1 + np.asarray(returns))

    # ------------------------------------------------------------------
    # Bootstrap Sharpe CI
    # ------------------------------------------------------------------

    @staticmethod
    def bootstrap_sharpe_ci(
        returns: np.ndarray | pd.Series,
        n_boot: int = 1000,
        ci: float = 0.95,
        seed: int = 42,
        periods_per_year: int = 252,
    ) -> dict[str, float]:
        """Bootstrap confidence interval for the annualised Sharpe ratio.

        Parameters
        ----------
        returns : periodic returns.
        n_boot : number of bootstrap resamples.
        ci : confidence level (e.g. 0.95 for 95 %).
        seed : RNG seed for reproducibility.
        periods_per_year : annualisation factor.

        Returns
        -------
        {"point_estimate": float, "ci_lower": float, "ci_upper": float}
        """
        rng = np.random.RandomState(seed)
        r = np.asarray(returns)
        n = len(r)

        def _sharpe(x: np.ndarray) -> float:
            std = np.std(x, ddof=1)
            if std < 1e-12:
                return 0.0
            return float(np.mean(x) / std * np.sqrt(periods_per_year))

        point = _sharpe(r)
        boot_sharpes = np.empty(n_boot)
        for i in range(n_boot):
            sample = rng.choice(r, size=n, replace=True)
            boot_sharpes[i] = _sharpe(sample)

        alpha = (1 - ci) / 2
        lower = float(np.percentile(boot_sharpes, alpha * 100))
        upper = float(np.percentile(boot_sharpes, (1 - alpha) * 100))

        return {
            "point_estimate": point,
            "ci_lower": lower,
            "ci_upper": upper,
        }
