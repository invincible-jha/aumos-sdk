# Copyright 2026 AumOS Enterprise
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Authentication helpers for the AumOS SDK.

Supports two authentication modes:
- API Key authentication (recommended for server-side usage)
- Bearer token authentication (for OAuth2 / short-lived tokens)

The client automatically refreshes bearer tokens when a ``token_refresher``
callable is provided.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Callable

from .exceptions import ConfigurationError


class AuthStrategy(ABC):
    """Abstract base for authentication strategies."""

    @abstractmethod
    def get_headers(self) -> dict[str, str]:
        """Return HTTP headers to attach to every outbound request."""
        ...

    @abstractmethod
    def is_valid(self) -> bool:
        """Return True if the credentials are currently usable."""
        ...


class ApiKeyAuth(AuthStrategy):
    """Authenticates using a static API key in the X-API-Key header.

    The API key can be provided directly or resolved from the
    ``AUMOS_API_KEY`` environment variable.

    Args:
        api_key: The API key string. If omitted, the environment variable
            ``AUMOS_API_KEY`` is used.

    Raises:
        ConfigurationError: If no API key can be found.

    Example:
        >>> auth = ApiKeyAuth(api_key="sk-aumos-...")
        >>> auth = ApiKeyAuth()  # reads from AUMOS_API_KEY env var
    """

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("AUMOS_API_KEY")
        if not resolved_key:
            raise ConfigurationError(
                "No API key provided. Pass api_key= or set the AUMOS_API_KEY "
                "environment variable."
            )
        self._api_key = resolved_key

    def get_headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    def is_valid(self) -> bool:
        return bool(self._api_key)

    def __repr__(self) -> str:
        masked = self._api_key[:8] + "..." if len(self._api_key) > 8 else "***"
        return f"ApiKeyAuth(api_key={masked!r})"


class BearerTokenAuth(AuthStrategy):
    """Authenticates using a Bearer token in the Authorization header.

    Optionally supports automatic token refresh via a ``token_refresher``
    callable that is invoked when the token is within ``refresh_buffer_seconds``
    of its expiry.

    Args:
        token: The initial bearer token.
        expires_at: Unix timestamp when the token expires. If None, the token
            is treated as non-expiring.
        token_refresher: Async callable that returns a new ``(token, expires_at)``
            tuple. Called automatically when the token is near expiry.
        refresh_buffer_seconds: How many seconds before expiry to refresh.
            Defaults to 60.

    Example:
        >>> auth = BearerTokenAuth(token="eyJ...", expires_at=time.time() + 3600)
    """

    def __init__(
        self,
        token: str,
        expires_at: float | None = None,
        token_refresher: Callable[[], tuple[str, float]] | None = None,
        refresh_buffer_seconds: float = 60.0,
    ) -> None:
        if not token:
            raise ConfigurationError("Bearer token must be a non-empty string.")
        self._token = token
        self._expires_at = expires_at
        self._token_refresher = token_refresher
        self._refresh_buffer_seconds = refresh_buffer_seconds

    def get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def is_valid(self) -> bool:
        if self._expires_at is None:
            return True
        return time.time() < self._expires_at - self._refresh_buffer_seconds

    def needs_refresh(self) -> bool:
        """Return True if the token should be refreshed before the next call."""
        if self._expires_at is None or self._token_refresher is None:
            return False
        return time.time() >= self._expires_at - self._refresh_buffer_seconds

    def update_token(self, token: str, expires_at: float | None = None) -> None:
        """Replace the current token with a freshly issued one."""
        self._token = token
        self._expires_at = expires_at

    def get_refresher(self) -> Callable[[], tuple[str, float]] | None:
        return self._token_refresher

    def __repr__(self) -> str:
        return f"BearerTokenAuth(expires_at={self._expires_at})"


def create_auth_strategy(
    api_key: str | None = None,
    token: str | None = None,
    expires_at: float | None = None,
    token_refresher: Callable[[], tuple[str, float]] | None = None,
) -> AuthStrategy:
    """Factory that creates the appropriate auth strategy.

    Preference order: explicit api_key > explicit token > AUMOS_API_KEY env var.

    Args:
        api_key: Static API key.
        token: Bearer token.
        expires_at: Expiry for the bearer token.
        token_refresher: Callable for refreshing bearer tokens.

    Returns:
        An :class:`AuthStrategy` instance.

    Raises:
        ConfigurationError: If no credentials are provided.
    """
    if api_key:
        return ApiKeyAuth(api_key=api_key)
    if token:
        return BearerTokenAuth(
            token=token,
            expires_at=expires_at,
            token_refresher=token_refresher,
        )
    if os.environ.get("AUMOS_API_KEY"):
        return ApiKeyAuth()
    raise ConfigurationError(
        "No authentication credentials found. Provide api_key=, token=, "
        "or set the AUMOS_API_KEY environment variable."
    )
