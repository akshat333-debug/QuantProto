"""Paper trading bridge — simulated broker for live testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone

import numpy as np
import pandas as pd


@dataclass
class Position:
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealised_pnl(self) -> float:
        return self.quantity * (self.current_price - self.avg_cost)


class PaperBroker:
    """Simulated broker for paper trading.

    Tracks positions, cash, and generates PnL attribution.
    """

    def __init__(self, initial_cash: float = 1_000_000.0, commission_bps: float = 5.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.commission_bps = commission_bps
        self.trade_log: list[dict] = []
        self.equity_snapshots: list[dict] = []

    def submit_order(
        self,
        ticker: str,
        quantity: float,
        price: float,
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        """Submit and immediately fill a market order."""
        ts = timestamp or datetime.now(timezone.utc)
        commission = abs(quantity * price) * self.commission_bps / 10_000

        if ticker in self.positions:
            pos = self.positions[ticker]
            old_qty = pos.quantity
            new_qty = old_qty + quantity
            if new_qty != 0 and old_qty != 0 and np.sign(old_qty) == np.sign(quantity):
                pos.avg_cost = (pos.avg_cost * old_qty + price * quantity) / new_qty
            elif new_qty != 0:
                pos.avg_cost = price
            pos.quantity = new_qty
            pos.current_price = price
            if pos.quantity == 0:
                del self.positions[ticker]
        else:
            if quantity != 0:
                self.positions[ticker] = Position(ticker, quantity, price, price)

        self.cash -= quantity * price + commission

        trade = {
            "timestamp": ts,
            "ticker": ticker,
            "quantity": quantity,
            "price": price,
            "commission": commission,
        }
        self.trade_log.append(trade)
        return trade

    def update_prices(self, prices: dict[str, float]) -> None:
        """Update current prices for all positions."""
        for ticker, price in prices.items():
            if ticker in self.positions:
                self.positions[ticker].current_price = price

    def snapshot(self, timestamp: datetime | None = None) -> dict[str, Any]:
        """Take equity snapshot."""
        ts = timestamp or datetime.now(timezone.utc)
        port_value = self.cash + sum(p.market_value for p in self.positions.values())
        snap = {
            "timestamp": ts,
            "cash": self.cash,
            "positions_value": sum(p.market_value for p in self.positions.values()),
            "total_equity": port_value,
            "n_positions": len(self.positions),
        }
        self.equity_snapshots.append(snap)
        return snap

    def pnl_attribution(self) -> dict[str, Any]:
        """Break down PnL into components."""
        total_equity = self.cash + sum(p.market_value for p in self.positions.values())
        total_pnl = total_equity - self.initial_cash
        total_commission = sum(t["commission"] for t in self.trade_log)
        unrealised = sum(p.unrealised_pnl for p in self.positions.values())

        return {
            "total_pnl": total_pnl,
            "unrealised_pnl": unrealised,
            "realised_pnl": total_pnl - unrealised,
            "total_commission": total_commission,
            "net_pnl": total_pnl - total_commission,
            "n_trades": len(self.trade_log),
        }

    def reconcile(self, expected: dict[str, float]) -> list[dict]:
        """Compare expected vs actual positions, report discrepancies."""
        diffs = []
        all_tickers = set(expected.keys()) | set(self.positions.keys())
        for ticker in all_tickers:
            expected_qty = expected.get(ticker, 0.0)
            actual_qty = self.positions[ticker].quantity if ticker in self.positions else 0.0
            if abs(expected_qty - actual_qty) > 1e-6:
                diffs.append({
                    "ticker": ticker,
                    "expected": expected_qty,
                    "actual": actual_qty,
                    "diff": actual_qty - expected_qty,
                })
        return diffs
