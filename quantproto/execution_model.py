"""Execution cost model: transaction costs, slippage, and market impact.

Models realistic execution frictions for backtesting.
All methods are deterministic and pure-functional.
"""

from __future__ import annotations


class ExecutionModel:
    """Compute execution costs for order fills."""

    @staticmethod
    def transaction_cost(notional: float, bps: float = 5.0) -> float:
        """Flat transaction cost in basis points.

        Parameters
        ----------
        notional : absolute dollar value of the trade.
        bps : cost in basis points (1 bp = 0.01 %).

        Returns
        -------
        Dollar cost of the transaction.
        """
        return notional * bps / 10_000

    @staticmethod
    def slippage(
        order_size: float,
        adv: float,
        price: float,
        impact_coeff: float = 0.1,
    ) -> float:
        """Square-root market impact slippage.

        slippage = impact_coeff × sqrt(order_size / adv) × price

        Parameters
        ----------
        order_size : number of shares in the order.
        adv : average daily volume (shares).
        price : current price per share.
        impact_coeff : impact scaling constant.

        Returns
        -------
        Dollar slippage cost.
        """
        if adv <= 0:
            raise ValueError("ADV must be positive")
        participation = order_size / adv
        return impact_coeff * (participation ** 0.5) * price

    @staticmethod
    def total_execution_cost(
        order_size: float,
        price: float,
        adv: float,
        bps: float = 5.0,
        impact_coeff: float = 0.1,
    ) -> float:
        """Combined transaction cost + slippage.

        Parameters
        ----------
        order_size : number of shares.
        price : price per share.
        adv : average daily volume.
        bps : transaction cost in basis points.
        impact_coeff : slippage impact coefficient.

        Returns
        -------
        Total dollar execution cost.
        """
        notional = order_size * price
        tc = ExecutionModel.transaction_cost(notional, bps)
        slip = ExecutionModel.slippage(order_size, adv, price, impact_coeff)
        return tc + slip
