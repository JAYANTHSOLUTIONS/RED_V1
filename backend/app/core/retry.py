"""Bounded asynchronous retry utility with exponential backoff and jitter.

Enforces strict reliability boundaries:
- Never retries indefinitely (strictly bounded attempts).
- Never retries non-retryable errors (validation, authentication, business logic conflicts).
- Retries transient I/O network errors (connection reset, timeout).
- Adds jitter to prevent thundering herd problems.
"""
import asyncio
import logging
import random
from typing import Any, Awaitable, Callable, Optional, Sequence, Tuple, Type, TypeVar

from app.core.exceptions import AppException

logger = logging.getLogger("red.reliability.retry")

T = TypeVar("T")

DEFAULT_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    TimeoutError,
    ConnectionError,
    OSError,
    asyncio.TimeoutError,
)


def is_transient_network_or_5xx(exc: Exception) -> bool:
    """Check if an exception is a transient network error or 5xx/429 HTTP status error."""
    if isinstance(exc, DEFAULT_RETRYABLE_EXCEPTIONS):
        return True

    exc_type = type(exc).__name__
    if any(k in exc_type for k in ("Timeout", "Connect", "Network", "RemoteProtocol")):
        return True

    resp = getattr(exc, "response", None)
    if resp is not None:
        status_code = getattr(resp, "status_code", None)
        if status_code in (429, 502, 503, 504):
            return True
    return False


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    op_name: str = "operation",
    max_attempts: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Sequence[Type[Exception]] = DEFAULT_RETRYABLE_EXCEPTIONS,
    retryable_check: Optional[Callable[[Exception], bool]] = None,
) -> T:
    """Execute an async operation with bounded retries on transient errors.

    Args:
        operation: Async callable to execute.
        op_name: Human-readable name for structured logging.
        max_attempts: Maximum number of attempts (must be >= 1).
        initial_delay: Initial delay in seconds before the first retry.
        max_delay: Maximum ceiling for delay between attempts.
        backoff_factor: Multiplier applied to delay after each failure.
        jitter: If True, adds a small random factor to the delay.
        retryable_exceptions: Tuple of exception types permitted to trigger a retry.

    Returns:
        The result of the successful operation.

    Raises:
        The last encountered exception if all attempts are exhausted or a non-retryable
        exception is encountered.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    delay = initial_delay
    attempt = 1

    while True:
        try:
            return await operation()
        except Exception as exc:
            # Never retry application business/security exceptions
            if isinstance(exc, AppException):
                logger.debug(f"{op_name} failed with non-retryable AppException: {exc}")
                raise

            # Check if exception is explicitly retryable
            if retryable_check is not None:
                is_retryable = retryable_check(exc)
            else:
                is_retryable = any(isinstance(exc, exc_cls) for exc_cls in retryable_exceptions)
            if not is_retryable or attempt >= max_attempts:
                if attempt >= max_attempts:
                    logger.warning(
                        f"{op_name} exhausted all {max_attempts} attempts. Final error: {exc}"
                    )
                raise

            # Calculate sleep duration with optional jitter
            sleep_duration = min(delay, max_delay)
            if jitter:
                sleep_duration += random.uniform(0.0, sleep_duration * 0.1)

            logger.info(
                f"{op_name} failed attempt {attempt}/{max_attempts} ({type(exc).__name__}: {exc}). "
                f"Retrying in {sleep_duration:.3f}s..."
            )

            await asyncio.sleep(sleep_duration)
            delay *= backoff_factor
            attempt += 1
