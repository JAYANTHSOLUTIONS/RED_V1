"""In-memory sliding-window rate limiter for brute-force prevention.

Monolithic, zero-dependency, thread-safe rate limiter.
Uses an in-memory sliding window of request timestamps per client key (e.g. IP address).
"""
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError


MAX_TRACKED_CLIENTS: int = 50_000


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter with memory bounding."""

    def __init__(self, max_tracked_clients: int = MAX_TRACKED_CLIENTS) -> None:
        self._lock = asyncio.Lock()
        self._requests: Dict[str, deque[float]] = {}
        self.max_tracked_clients = max_tracked_clients

    def _prune_stale_locked(self, cutoff: float) -> None:
        """Prune keys with no active timestamps within the sliding window."""
        stale_keys = [
            k for k, q in self._requests.items()
            if not q or q[-1] <= cutoff
        ]
        for k in stale_keys:
            del self._requests[k]

    async def check_rate_limit(
        self,
        key: str,
        max_attempts: int,
        window_seconds: int,
    ) -> None:
        """Check if an action exceeds the rate limit.

        Raises:
            RateLimitedError: If maximum attempts within the sliding window are exceeded.
        """
        if not key:
            return

        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - window_seconds

        async with self._lock:
            # Memory ceiling check: if dictionary is growing too large, prune stale keys
            if len(self._requests) >= self.max_tracked_clients:
                self._prune_stale_locked(cutoff)
                if len(self._requests) >= self.max_tracked_clients:
                    raise RateLimitedError(
                        "Rate limiter capacity reached. Please try again later."
                    )

            if key not in self._requests:
                self._requests[key] = deque()

            queue = self._requests[key]
            # Evict timestamps older than the sliding window
            while queue and queue[0] <= cutoff:
                queue.popleft()

            if len(queue) >= max_attempts:
                raise RateLimitedError(
                    f"Too many requests. Rate limit exceeded. Please try again after {window_seconds} seconds."
                )

            queue.append(now)

    async def prune_stale(self, window_seconds: int) -> int:
        """Manually prune stale clients. Returns count of pruned keys."""
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - window_seconds
        async with self._lock:
            initial_count = len(self._requests)
            self._prune_stale_locked(cutoff)
            return initial_count - len(self._requests)

    async def reset(self) -> None:
        """Clear all tracked request history (useful for test isolation)."""
        async with self._lock:
            self._requests.clear()


_login_rate_limiter = SlidingWindowRateLimiter()


def get_login_rate_limiter() -> SlidingWindowRateLimiter:
    return _login_rate_limiter


async def check_login_rate_limit(request: Request) -> None:
    """FastAPI dependency to rate-limit authentication requests by client IP."""
    settings = get_settings()
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    else:
        ip = "unknown"

    await _login_rate_limiter.check_rate_limit(
        key=f"login:{ip}",
        max_attempts=settings.RATE_LIMIT_LOGIN_ATTEMPTS,
        window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
    )
