"""Data loader for demo pipeline.

Generates a synthetic universe of stocks with deterministic pricing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_UNIVERSE = ["AAPL", "GOOG", "MSFT", "AMZN", "META"]


def load_universe(tickers: list[str] | None = None) -> list[str]:
    """Return the stock universe for the demo.

    Parameters
    ----------
    tickers : optional custom list; defaults to DEFAULT_UNIVERSE.

    Returns
    -------
    List of ticker strings.
    """
    return tickers or list(DEFAULT_UNIVERSE)


def generate_prices(
    tickers: list[str],
    n_days: int = 504,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic close prices via geometric Brownian motion.

    Parameters
    ----------
    tickers : list of ticker symbols.
    n_days : number of trading days.
    seed : RNG seed for determinism.

    Returns
    -------
    DataFrame with index=dates, columns=tickers.
    """
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2022-01-03", periods=n_days)

    data = {}
    for i, ticker in enumerate(tickers):
        # Each ticker has slightly different drift/vol
        mu = 0.0003 + 0.0001 * (i % 3)
        sigma = 0.015 + 0.005 * (i % 4)
        returns = rng.normal(mu, sigma, n_days)
        prices = 100.0 * np.exp(np.cumsum(returns))
        data[ticker] = prices

    return pd.DataFrame(data, index=dates)
