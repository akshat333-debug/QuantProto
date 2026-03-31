"""Real data fetcher with caching.

Wraps yfinance for downloading market data with local CSV caching.
Falls back to synthetic data generation if yfinance is unavailable.
"""

from __future__ import annotations

import os
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CACHE_DIR = Path.home() / ".quantproto" / "data_cache"


def _cache_key(tickers: list[str], start: str, end: str) -> str:
    raw = f"{'_'.join(sorted(tickers))}_{start}_{end}"
    return hashlib.md5(raw.encode()).hexdigest()


def fetch_prices(
    tickers: list[str],
    start: str = "2020-01-01",
    end: str = "2024-01-01",
    cache: bool = True,
) -> pd.DataFrame:
    """Fetch daily close prices.

    Tries yfinance first, falls back to synthetic data.
    Caches results as CSV for offline reproducibility.

    Parameters
    ----------
    tickers : list of ticker symbols.
    start : start date string "YYYY-MM-DD".
    end : end date string "YYYY-MM-DD".
    cache : whether to use/save local cache.

    Returns
    -------
    DataFrame with index=DatetimeIndex, columns=tickers.
    """
    if cache:
        cached = _load_cache(tickers, start, end)
        if cached is not None:
            return cached

    try:
        import yfinance as yf
        data = yf.download(tickers, start=start, end=end, progress=False)
        if data.empty:
            return _generate_synthetic(tickers, start, end)
        if isinstance(data.columns, pd.MultiIndex):
            prices = data["Close"]
        else:
            prices = data[["Close"]]
            prices.columns = tickers
        prices = prices.dropna()
        if prices.empty:
            return _generate_synthetic(tickers, start, end)
        if cache:
            _save_cache(prices, tickers, start, end)
        return prices
    except (ImportError, Exception):
        # Fallback to synthetic
        return _generate_synthetic(tickers, start, end)


def _generate_synthetic(
    tickers: list[str], start: str, end: str
) -> pd.DataFrame:
    """Generate synthetic prices as fallback."""
    dates = pd.bdate_range(start, end)
    rng = np.random.RandomState(42)
    data = {}
    for i, ticker in enumerate(tickers):
        mu = 0.0003 + 0.0001 * (i % 3)
        sigma = 0.015 + 0.005 * (i % 4)
        returns = rng.normal(mu, sigma, len(dates))
        data[ticker] = 100.0 * np.exp(np.cumsum(returns))
    return pd.DataFrame(data, index=dates)


def _load_cache(tickers: list[str], start: str, end: str) -> pd.DataFrame | None:
    key = _cache_key(tickers, start, end)
    path = CACHE_DIR / f"{key}.csv"
    if path.exists():
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df
    return None


def _save_cache(df: pd.DataFrame, tickers: list[str], start: str, end: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(tickers, start, end)
    path = CACHE_DIR / f"{key}.csv"
    df.to_csv(path)
