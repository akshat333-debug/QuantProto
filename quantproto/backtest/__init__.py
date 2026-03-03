"""Event-driven backtester.

Event queue architecture: MarketData → Signal → Order → Fill.
Supports market, limit, stop orders and latency simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np
import pandas as pd


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class EventType(Enum):
    MARKET_DATA = "market_data"
    SIGNAL = "signal"
    ORDER = "order"
    FILL = "fill"


@dataclass
class Event:
    event_type: EventType
    timestamp: pd.Timestamp
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    ticker: str
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    stop_price: float | None = None
    timestamp: pd.Timestamp | None = None


@dataclass
class Fill:
    ticker: str
    quantity: float
    fill_price: float
    timestamp: pd.Timestamp
    commission: float = 0.0


class EventBacktester:
    """Event-driven backtester with order management.

    Parameters
    ----------
    prices : DataFrame of close prices.
    signal_fn : function(positions, prices_so_far, timestamp) -> list[Order]
    latency : number of bars delay between signal and fill.
    commission_bps : commission in basis points.
    """

    def __init__(
        self,
        prices: pd.DataFrame,
        signal_fn: Callable,
        latency: int = 1,
        commission_bps: float = 5.0,
    ):
        self.prices = prices
        self.signal_fn = signal_fn
        self.latency = latency
        self.commission_bps = commission_bps

    def run(self) -> dict[str, Any]:
        """Execute the event-driven backtest.

        Returns
        -------
        {
            "equity_curve": Series,
            "fills": list[Fill],
            "positions": dict history,
            "returns": Series,
        }
        """
        tickers = list(self.prices.columns)
        positions = {t: 0.0 for t in tickers}
        cash = 1_000_000.0
        pending_orders: list[tuple[int, Order]] = []  # (fill_bar_idx, order)
        fills: list[Fill] = []
        equity_history = []
        dates = self.prices.index

        for i in range(len(dates)):
            timestamp = dates[i]
            current_prices = self.prices.iloc[i]

            # Process pending orders that are due
            new_pending = []
            for fill_idx, order in pending_orders:
                if i >= fill_idx:
                    fill = self._try_fill(order, current_prices, timestamp)
                    if fill:
                        fills.append(fill)
                        positions[fill.ticker] += fill.quantity
                        cash -= fill.fill_price * fill.quantity + fill.commission
                else:
                    new_pending.append((fill_idx, order))
            pending_orders = new_pending

            # Generate new signals
            prices_so_far = self.prices.iloc[:i + 1]
            orders = self.signal_fn(dict(positions), prices_so_far, timestamp)
            if orders:
                for order in orders:
                    order.timestamp = timestamp
                    pending_orders.append((i + self.latency, order))

            # Calculate equity
            port_value = cash + sum(
                positions[t] * current_prices[t] for t in tickers
            )
            equity_history.append(port_value)

        equity = pd.Series(equity_history, index=dates)
        returns = equity.pct_change().fillna(0)

        return {
            "equity_curve": equity,
            "fills": fills,
            "returns": returns,
            "n_fills": len(fills),
        }

    def _try_fill(
        self, order: Order, prices: pd.Series, timestamp: pd.Timestamp
    ) -> Fill | None:
        """Attempt to fill an order at current prices."""
        if order.ticker not in prices.index:
            return None

        price = prices[order.ticker]
        commission = abs(order.quantity * price) * self.commission_bps / 10_000

        if order.order_type == OrderType.MARKET:
            return Fill(order.ticker, order.quantity, price, timestamp, commission)

        elif order.order_type == OrderType.LIMIT:
            if order.limit_price is None:
                return None
            # Buy limit: fill if price <= limit
            if order.quantity > 0 and price <= order.limit_price:
                return Fill(order.ticker, order.quantity, price, timestamp, commission)
            # Sell limit: fill if price >= limit
            if order.quantity < 0 and price >= order.limit_price:
                return Fill(order.ticker, order.quantity, price, timestamp, commission)

        elif order.order_type == OrderType.STOP:
            if order.stop_price is None:
                return None
            # Buy stop: fill if price >= stop
            if order.quantity > 0 and price >= order.stop_price:
                return Fill(order.ticker, order.quantity, price, timestamp, commission)
            # Sell stop: fill if price <= stop
            if order.quantity < 0 and price <= order.stop_price:
                return Fill(order.ticker, order.quantity, price, timestamp, commission)

        return None
