"""Rate limiting for MCP tool calls.

Provides an in-process token-bucket (:class:`RateLimiter`) and a Redis-backed
distributed limiter (:class:`RedisRateLimiter`). :func:`build_rate_limiter`
selects Redis when ``REDIS_URL`` is set and reachable, otherwise the in-memory
bucket — so a single process works with zero infra, and a multi-replica
``docker compose`` deployment shares one limit via Redis.
"""

from __future__ import annotations

import os
import time
import threading
import logging

logger = logging.getLogger("quantproto.mcp.rate_limit")


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


# Atomic token-bucket in Redis: refill by elapsed time, then try to consume.
_BUCKET_LUA = """
local key = KEYS[1]
local max_tokens = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])
local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then tokens = max_tokens; ts = now end
local elapsed = math.max(0, now - ts)
tokens = math.min(max_tokens, tokens + elapsed * refill_rate)
local allowed = 0
if tokens >= requested then tokens = tokens - requested; allowed = 1 end
redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, math.ceil(max_tokens / refill_rate) + 1)
return {allowed, tostring(tokens)}
"""


class RedisRateLimiter:
    """Distributed token-bucket rate limiter backed by Redis.

    Same ``consume`` / ``reset`` interface as :class:`RateLimiter`, but the
    bucket is shared across processes/replicas via an atomic Lua script.
    """

    def __init__(self, client, max_tokens: int = 60, refill_rate: float = 1.0,
                 key: str = "quantproto:ratelimit"):
        self.client = client
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.key = key
        self._script = client.register_script(_BUCKET_LUA)

    def consume(self, tokens: int = 1) -> None:
        allowed, remaining = self._script(
            keys=[self.key],
            args=[self.max_tokens, self.refill_rate, time.time(), tokens],
        )
        if int(allowed) != 1:
            raise RateLimitError(
                f"Rate limit exceeded. Available: {remaining}, requested: {tokens}"
            )

    def reset(self) -> None:
        self.client.delete(self.key)


def build_rate_limiter(max_tokens: int = 60, refill_rate: float = 1.0):
    """Return a Redis limiter when ``REDIS_URL`` is reachable, else in-memory."""
    url = os.getenv("REDIS_URL")
    if url:
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(url)
            client.ping()
            logger.info("Rate limiting via Redis at %s", url)
            return RedisRateLimiter(client, max_tokens, refill_rate)
        except Exception as e:
            logger.warning("Redis unavailable (%s); using in-memory rate limiter.", e)
    return RateLimiter(max_tokens, refill_rate)
