"""Universe management with survivorship bias handling."""

from __future__ import annotations

from typing import Any

import pandas as pd


# S&P 500 top 30 (simplified — real version would fetch from source)
SP500_TOP30 = [
    "AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "JPM", "V", "PG", "XOM", "HD", "CVX", "MA", "ABBV",
    "MRK", "LLY", "COST", "PEP", "KO", "AVGO", "WMT", "TMO", "CSCO",
    "ACN", "MCD", "ABT",
]


class UniverseManager:
    """Manage stock universe with survivorship-bias-aware operations."""

    def __init__(self, tickers: list[str] | None = None):
        self.tickers = tickers or list(SP500_TOP30[:10])

    def get_universe(self) -> list[str]:
        return list(self.tickers)

    def add(self, ticker: str) -> None:
        if ticker not in self.tickers:
            self.tickers.append(ticker)

    def remove(self, ticker: str) -> None:
        if ticker in self.tickers:
            self.tickers.remove(ticker)

    def filter_by_data_availability(
        self, prices: pd.DataFrame, min_pct: float = 0.9
    ) -> list[str]:
        """Filter tickers to those with at least min_pct non-NaN data."""
        available = []
        for col in prices.columns:
            if col in self.tickers:
                pct = prices[col].notna().mean()
                if pct >= min_pct:
                    available.append(col)
        return available

    def to_dict(self) -> dict[str, Any]:
        return {"tickers": self.tickers, "count": len(self.tickers)}
