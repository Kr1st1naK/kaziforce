"""
A sliding-window rate limit, kept in memory.

Used on the one endpoint that releases a person's name and phone number to someone else
(GET /workers/<public_id>), so that a client cannot page through contact details quickly.

It is per process and forgets on restart. Behind several workers each would count separately,
so the effective limit is the limit times the number of workers; a deployment that needs the
limit to hold would move this to a shared store. It also limits by account, so signing in
again does not reset it, but it cannot stop someone creating new accounts, because creating
one needs only an unverified phone number (docs/limitations.md).
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable

MAX_KEYS = 10_000  # beyond this, idle keys are dropped on the next call


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        if limit < 1 or window_seconds <= 0:
            raise ValueError("a limit needs at least one call and a positive window")
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int | None:
        """Record a call. None if it is allowed, else the whole seconds to wait before the next."""
        now = self._clock()
        with self._lock:
            if len(self._hits) > MAX_KEYS:
                self._hits = {k: h for k, h in self._hits.items() if h and now - h[-1] < self.window}
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, math.ceil(self.window - (now - hits[0])))
            hits.append(now)
            return None
