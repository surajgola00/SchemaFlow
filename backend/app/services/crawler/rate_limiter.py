"""
Per-domain token-bucket async rate limiter.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict


class DomainRateLimiter:
    def __init__(self, rps: float = 1.0) -> None:
        self.rps = rps
        self._interval = 1.0 / max(0.1, rps)
        self._last_request_time: dict[str, float] = defaultdict(float)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, domain: str) -> None:
        lock = self._locks[domain]
        async with lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time[domain]
            if elapsed < self._interval:
                delay = self._interval - elapsed
                await asyncio.sleep(delay)
            self._last_request_time[domain] = time.monotonic()


rate_limiter = DomainRateLimiter()
