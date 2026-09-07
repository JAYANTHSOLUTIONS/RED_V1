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


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._requests: Dict[str, deque[float]] = defaultdict(deque)

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
            queue = self._requests[key]
            # Evict timestamps older than the sliding window
            while queue and queue[0] <= cutoff:
                queue.popleft()

            if len(queue) >= max_attempts:
                raise RateLimitedError(
                    f"Too many requests. Rate limit exceeded. Please try again after {window_seconds} seconds."
                )

            queue.append(now)

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
