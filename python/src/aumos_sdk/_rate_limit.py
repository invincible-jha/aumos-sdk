"""Rate limit state parsing for the AumOS Python SDK.

Parses X-RateLimit-* headers returned by the AumOS API and exposes them on
response objects so callers can proactively throttle before hitting 429 errors.

Standard headers:
    X-RateLimit-Limit     — requests allowed per window
    X-RateLimit-Remaining — requests remaining in the current window
    X-RateLimit-Reset     — Unix timestamp when the window resets
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass(frozen=True)
class RateLimitState:
    """Immutable snapshot of rate limit state from an API response.

    All values may be None if the server does not return rate limit headers
    (e.g., during sandbox/testing environments).
    """

    limit: Optional[int]
    remaining: Optional[int]
    reset_at: Optional[int]

    @classmethod
    def from_response(cls, response: httpx.Response) -> "RateLimitState":
        """Parse rate limit state from an httpx response.

        Args:
            response: The httpx response to parse headers from.

        Returns:
            A RateLimitState instance. Values are None if headers are absent.
        """
        return cls(
            limit=_parse_int_header(response, "X-RateLimit-Limit"),
            remaining=_parse_int_header(response, "X-RateLimit-Remaining"),
            reset_at=_parse_int_header(response, "X-RateLimit-Reset"),
        )

    @property
    def is_exhausted(self) -> bool:
        """Return True if no requests remain in the current window."""
        return self.remaining is not None and self.remaining <= 0

    def __repr__(self) -> str:
        return (
            f"RateLimitState("
            f"limit={self.limit}, "
            f"remaining={self.remaining}, "
            f"reset_at={self.reset_at})"
        )


def _parse_int_header(response: httpx.Response, header_name: str) -> Optional[int]:
    """Parse an integer header value from an httpx response.

    Args:
        response: The httpx response to read headers from.
        header_name: Case-insensitive header name.

    Returns:
        The parsed integer, or None if the header is absent or non-numeric.
    """
    value = response.headers.get(header_name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
