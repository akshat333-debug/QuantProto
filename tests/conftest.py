"""Global test fixtures for QuantProto."""

import random

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def seed_rng():
    """Seed all RNGs for deterministic tests."""
    np.random.seed(42)
    random.seed(42)
    yield


@pytest.fixture
def sample_prices():
    """200-row daily OHLCV DataFrame for 5 tickers.

    Generates synthetic price data using geometric Brownian motion
    with fixed seed for reproducibility.
    """
    np.random.seed(42)
    n_days = 200
    tickers = ["AAPL", "GOOG", "MSFT", "AMZN", "META"]
    dates = pd.bdate_range("2023-01-01", periods=n_days)

    data = {}
    for ticker in tickers:
        # GBM: S(t) = S(0) * exp((mu - 0.5*sigma^2)*t + sigma*W(t))
        mu, sigma = 0.0005, 0.02
        returns = np.random.normal(mu, sigma, n_days)
        close = 100.0 * np.exp(np.cumsum(returns))
        high = close * (1 + np.abs(np.random.normal(0, 0.005, n_days)))
        low = close * (1 - np.abs(np.random.normal(0, 0.005, n_days)))
        open_ = close * (1 + np.random.normal(0, 0.003, n_days))
        volume = np.random.randint(1_000_000, 10_000_000, n_days).astype(float)

        data[ticker] = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
            index=dates,
        )

    # Return a dict of DataFrames and also a simple close-price DataFrame
    close_df = pd.DataFrame({t: data[t]["close"] for t in tickers}, index=dates)
    return close_df


@pytest.fixture
def sample_returns(sample_prices):
    """Daily returns from sample_prices."""
    return sample_prices.pct_change().dropna()
