"""Tests for rate limiter — Phase F7 validation."""

import time

import pytest

from quantproto.mcp.rate_limit import RateLimiter, RateLimitError


class TestRateLimiter:
    def test_within_limit_succeeds(self):
        limiter = RateLimiter(max_tokens=10, refill_rate=1.0)
        for _ in range(10):
            limiter.consume()  # should not raise

    def test_exceeding_limit_raises(self):
        limiter = RateLimiter(max_tokens=3, refill_rate=0.0)  # no refill
        limiter.consume()
        limiter.consume()
        limiter.consume()
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            limiter.consume()

    def test_refill_restores_tokens(self):
        limiter = RateLimiter(max_tokens=2, refill_rate=100.0)  # fast refill
        limiter.consume()
        limiter.consume()
        time.sleep(0.05)  # 50ms * 100 tokens/sec = 5 tokens refilled
        limiter.consume()  # should succeed after refill

    def test_reset(self):
        limiter = RateLimiter(max_tokens=1, refill_rate=0.0)
        limiter.consume()
        with pytest.raises(RateLimitError):
            limiter.consume()
        limiter.reset()
        limiter.consume()  # should succeed after reset

    def test_burst_capacity(self):
        limiter = RateLimiter(max_tokens=100, refill_rate=0.0)
        for _ in range(100):
            limiter.consume()
        with pytest.raises(RateLimitError):
            limiter.consume()
