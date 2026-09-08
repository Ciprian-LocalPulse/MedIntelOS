"""In-memory, per-process token-bucket rate limiter.

Boundary: state lives in this process's memory. Fine for a single instance;
multiple API instances behind a load balancer each enforce their own limit
independently, so the effective limit scales with instance count. A shared
limiter (e.g. Redis-backed) is needed before that matters — see
docs/ROADMAP.md 0.4.0.
"""

from __future__ import annotations

import threading
import time


class TokenBucketLimiter:
    def __init__(self, requests_per_minute: int, burst: int) -> None:
        if requests_per_minute <= 0 or burst <= 0:
            raise ValueError("requests_per_minute and burst must both be positive")
        self._refill_rate = requests_per_minute / 60.0  # tokens per second
        self._capacity = float(burst)
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_refill)

    def allow(self, key: str) -> tuple[bool, float]:
        """Returns (allowed, retry_after_seconds). retry_after_seconds is 0 when allowed."""
        now = time.monotonic()
        with self._lock:
            tokens, last_refill = self._buckets.get(key, (self._capacity, now))
            elapsed = now - last_refill
            tokens = min(self._capacity, tokens + elapsed * self._refill_rate)

            if tokens >= 1.0:
                tokens -= 1.0
                self._buckets[key] = (tokens, now)
                return True, 0.0

            self._buckets[key] = (tokens, now)
            missing = 1.0 - tokens
            retry_after = missing / self._refill_rate
            return False, retry_after

    def evict_stale(self, older_than_seconds: float = 3600.0) -> int:
        """Drops buckets untouched for a while, so long-running processes with
        many distinct callers (one bucket per API key/IP) don't grow this
        dict unboundedly. Not called automatically; wire into a periodic
        task if running with a very large, high-churn client population.
        """
        now = time.monotonic()
        with self._lock:
            stale = [k for k, (_, last) in self._buckets.items() if now - last > older_than_seconds]
            for k in stale:
                del self._buckets[k]
            return len(stale)
