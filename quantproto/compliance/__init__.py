"""Compliance and audit trail.

Immutable audit log, pre-trade compliance checks, and reporting.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any


class AuditLog:
    """Immutable, hash-chained audit log.

    Every entry is hashed with the previous entry's hash,
    creating a tamper-evident chain.
    """

    def __init__(self):
        self._entries: list[dict] = []
        self._last_hash = "genesis"

    def log(
        self,
        event_type: str,
        data: dict[str, Any],
        agent_id: str = "system",
    ) -> dict[str, Any]:
        """Append an immutable log entry."""
        entry = {
            "index": len(self._entries),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent_id": agent_id,
            "data": data,
            "prev_hash": self._last_hash,
        }
        entry["hash"] = self._hash_entry(entry)
        self._last_hash = entry["hash"]
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire log chain."""
        prev = "genesis"
        for entry in self._entries:
            if entry["prev_hash"] != prev:
                return False
            expected = self._hash_entry(
                {k: v for k, v in entry.items() if k != "hash"}
            )
            if entry["hash"] != expected:
                return False
            prev = entry["hash"]
        return True

    def get_entries(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
    ) -> list[dict]:
        """Query log entries with optional filters."""
        results = self._entries
        if event_type:
            results = [e for e in results if e["event_type"] == event_type]
        if agent_id:
            results = [e for e in results if e["agent_id"] == agent_id]
        return results

    @property
    def length(self) -> int:
        return len(self._entries)

    @staticmethod
    def _hash_entry(entry: dict) -> str:
        raw = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()


class PreTradeCompliance:
    """Pre-trade compliance checks.

    Validates orders against configurable rules before execution.
    """

    def __init__(
        self,
        max_position_pct: float = 0.10,
        max_sector_pct: float = 0.30,
        max_order_value: float = 1_000_000.0,
        restricted_tickers: list[str] | None = None,
    ):
        self.max_position_pct = max_position_pct
        self.max_sector_pct = max_sector_pct
        self.max_order_value = max_order_value
        self.restricted_tickers = set(restricted_tickers or [])

    def check(
        self,
        ticker: str,
        quantity: float,
        price: float,
        total_equity: float,
        current_positions: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Run pre-trade compliance checks.

        Returns
        -------
        {"passed": bool, "violations": list[str]}
        """
        violations = []
        order_value = abs(quantity * price)

        # Restricted ticker
        if ticker in self.restricted_tickers:
            violations.append(f"Restricted ticker: {ticker}")

        # Max order value
        if order_value > self.max_order_value:
            violations.append(
                f"Order value {order_value:.0f} exceeds max {self.max_order_value:.0f}"
            )

        # Max position concentration
        if total_equity > 0:
            position_pct = order_value / total_equity
            if position_pct > self.max_position_pct:
                violations.append(
                    f"Position {position_pct:.1%} exceeds max {self.max_position_pct:.1%}"
                )

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "order_value": order_value,
            "ticker": ticker,
        }
