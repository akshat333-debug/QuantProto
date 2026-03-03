"""Token-bucket rate limiter for MCP tool calls."""

from __future__ import annotations

import time
import threading


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


class RateLimiter:
    """Thread-safe token-bucket rate limiter.

    Parameters
    ----------
    max_tokens : maximum burst capacity.
    refill_rate : tokens added per second.
    """

    def __init__(self, max_tokens: int = 60, refill_rate: float = 1.0):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self._tokens = float(max_tokens)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_tokens, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> None:
        """Consume tokens or raise RateLimitError."""
        with self._lock:
            self._refill()
            if self._tokens < tokens:
                raise RateLimitError(
                    f"Rate limit exceeded. Available: {self._tokens:.1f}, "
                    f"requested: {tokens}"
                )
            self._tokens -= tokens

    def reset(self) -> None:
        """Reset to full capacity (useful for testing)."""
        with self._lock:
            self._tokens = float(self.max_tokens)
            self._last_refill = time.monotonic()
