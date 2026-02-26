# Copyright 2026 AumOS Enterprise
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""AumOS SDK exception hierarchy.

All SDK exceptions inherit from AumOSError, making it easy to catch
any SDK-raised error with a single except clause.
"""

from __future__ import annotations

from typing import Any


class AumOSError(Exception):
    """Base exception for all AumOS SDK errors."""

    def __init__(self, message: str, request_id: str | None = None) -> None:
        super().__init__(message)
        self.request_id = request_id

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)!r})"


class AumOSAPIError(AumOSError):
    """An error response returned by the AumOS API.

    Attributes:
        status_code: HTTP status code from the response.
        error_code: Machine-readable error code (e.g., "agent_not_found").
        details: Additional structured details from the response body.
        request_id: Correlation ID for support tickets.
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, request_id=request_id)
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status_code={self.status_code}, "
            f"error_code={self.error_code!r}, "
            f"message={str(self)!r}"
            f")"
        )


class AuthenticationError(AumOSAPIError):
    """Raised when the API returns a 401 Unauthorized response.

    This typically means your API key is missing, invalid, or expired.
    Check that you have set AUMOS_API_KEY correctly.
    """


class PermissionError(AumOSAPIError):
    """Raised when the API returns a 403 Forbidden response.

    Your credentials are valid but you lack permission for the requested
    operation. Check that your API key has the required scopes.
    """


class NotFoundError(AumOSAPIError):
    """Raised when the requested resource does not exist (404)."""


class ValidationError(AumOSAPIError):
    """Raised when the request body fails API-side validation (422).

    The ``details`` attribute contains per-field error information.
    """


class RateLimitError(AumOSAPIError):
    """Raised when the API returns a 429 Too Many Requests response.

    Attributes:
        retry_after: Seconds to wait before retrying, if provided by the API.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status_code, error_code, details, request_id)
        self.retry_after = retry_after


class ServerError(AumOSAPIError):
    """Raised for 5xx server-side errors."""


class TimeoutError(AumOSError):
    """Raised when a request exceeds the configured timeout."""


class ConnectionError(AumOSError):
    """Raised when the SDK cannot connect to the AumOS API.

    This may indicate a network issue or an incorrect base URL.
    """


class ConfigurationError(AumOSError):
    """Raised for invalid SDK configuration (missing credentials, etc.)."""
