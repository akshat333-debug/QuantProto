"""Tests for rate limiter — Phase F7 validation."""

import time

import pytest

from quantproto.mcp.rate_limit import RateLimiter, RateLimitError, build_rate_limiter


class TestBuildRateLimiter:
    def test_falls_back_to_in_memory(self, monkeypatch):
        # No REDIS_URL → in-memory token bucket.
        monkeypatch.delenv("REDIS_URL", raising=False)
        rl = build_rate_limiter(max_tokens=5, refill_rate=1.0)
        assert isinstance(rl, RateLimiter)

    def test_unreachable_redis_falls_back(self, monkeypatch):
        # REDIS_URL set but unreachable → graceful fallback, no crash.
        monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6390/0")
        rl = build_rate_limiter(max_tokens=5, refill_rate=1.0)
        assert isinstance(rl, RateLimiter)
        rl.consume()


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
