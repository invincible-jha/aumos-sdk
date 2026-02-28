"""Exponential backoff retry logic for the AumOS Python SDK.

Implements the "full jitter" strategy from AWS architecture blog:
delay = random(0, min(cap, base * 2^attempt))

Usage:
    result = await with_retry(lambda: client._http.get("/agents"))
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import TypeVar

import httpx

T = TypeVar("T")

RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BASE_DELAY_SECONDS: float = 0.5
DEFAULT_MAX_DELAY_SECONDS: float = 60.0


async def with_retry(
    func: Callable[[], T],
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY_SECONDS,
    max_delay: float = DEFAULT_MAX_DELAY_SECONDS,
) -> T:
    """Execute an async callable with exponential backoff retry on transient failures.

    Uses full jitter strategy: delay = random(0, min(cap, base * 2^attempt)).
    Respects the Retry-After header on 429 responses.

    Args:
        func: Async callable to execute and retry on transient failure.
        max_retries: Maximum number of retry attempts after the initial attempt (default 3).
        base_delay: Base delay in seconds for the first retry (default 0.5).
        max_delay: Maximum delay cap in seconds (default 60.0).

    Returns:
        The return value of func on success.

    Raises:
        httpx.HTTPStatusError: On non-retryable HTTP errors.
        AumOSError: After max_retries exhausted.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func()  # type: ignore[return-value]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in RETRYABLE_STATUS_CODES:
                raise
            last_error = exc
            if exc.response.status_code == 429:
                retry_after_header = exc.response.headers.get("Retry-After")
                if retry_after_header is not None:
                    delay = min(float(retry_after_header), max_delay)
                else:
                    cap = min(max_delay, base_delay * (2**attempt))
                    delay = random.uniform(0, cap)
            else:
                cap = min(max_delay, base_delay * (2**attempt))
                delay = random.uniform(0, cap)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            last_error = exc
            cap = min(max_delay, base_delay * (2**attempt))
            delay = random.uniform(0, cap)

        if attempt < max_retries:
            await asyncio.sleep(delay)

    raise RuntimeError(
        f"AumOS request failed after {max_retries} retries: {last_error}"
    ) from last_error
