"""Real data fetcher with caching.

Wraps yfinance for downloading market data with local CSV caching.
Falls back to synthetic data generation if yfinance is unavailable.
"""

from __future__ import annotations

import os
import hashlib
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CACHE_DIR = Path.home() / ".quantproto" / "data_cache"

logger = logging.getLogger("quantproto.data.fetcher")


class LiveDataError(RuntimeError):
    """Raised when live market data is requested but cannot be obtained.

    Surfacing this instead of silently returning synthetic data is critical:
    an integrity tool must never let a user believe they audited real prices
    when they actually audited fabricated ones.
    """


def _cache_key(tickers: list[str], start: str, end: str) -> str:
    raw = f"{'_'.join(sorted(tickers))}_{start}_{end}"
    return hashlib.md5(raw.encode()).hexdigest()


def fetch_prices(
    tickers: list[str],
    start: str = "2020-01-01",
    end: str = "2024-01-01",
    cache: bool = True,
    allow_synthetic_fallback: bool = False,
) -> pd.DataFrame:
    """Fetch daily close prices from Yahoo Finance.

    Tries the local CSV cache, then yfinance. If live data cannot be obtained
    it **fails loudly** by default (raising :class:`LiveDataError`) rather than
    silently fabricating prices — the caller must opt in to synthetic fallback.

    Parameters
    ----------
    tickers : list of ticker symbols.
    start : start date string "YYYY-MM-DD".
    end : end date string "YYYY-MM-DD".
    cache : whether to use/save local cache.
    allow_synthetic_fallback : if True, return synthetic data when live data is
        unavailable (clearly an explicit, opt-in choice). Default False.

    Returns
    -------
    DataFrame with index=DatetimeIndex, columns=tickers.

    Raises
    ------
    LiveDataError : when live data is unavailable and fallback is not allowed.
    """
    if cache:
        cached = _load_cache(tickers, start, end)
        if cached is not None:
            return cached

    def _fallback_or_raise(reason: str) -> pd.DataFrame:
        if allow_synthetic_fallback:
            logger.warning("Live data unavailable (%s); using synthetic fallback.", reason)
            return _generate_synthetic(tickers, start, end)
        raise LiveDataError(
            f"Could not fetch live data for {tickers} ({start}…{end}): {reason}. "
            "Pass allow_synthetic_fallback=True to use synthetic prices instead."
        )

    try:
        import yfinance as yf
    except ImportError:
        return _fallback_or_raise("yfinance not installed (pip install '.[live]')")

    try:
        data = yf.download(tickers, start=start, end=end, progress=False)
    except Exception as e:  # network / API failure
        logger.warning("yfinance download failed: %s", e)
        return _fallback_or_raise(f"download error: {e}")

    if data.empty:
        return _fallback_or_raise("no rows returned")
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]]
        prices.columns = tickers
    prices = prices.dropna()
    if prices.empty:
        return _fallback_or_raise("all rows NaN after cleaning")
    if cache:
        _save_cache(prices, tickers, start, end)
    return prices


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
