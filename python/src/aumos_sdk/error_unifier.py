"""Cross-language error unification module for the AumOS SDK.

Maps AumOS platform HTTP error codes to the SDK exception hierarchy, provides
retry hints, generates error documentation, and ensures consistent error handling
semantics across Python, TypeScript, Go, and Java SDK implementations.
"""

from typing import Any

from aumos_sdk.exceptions import (
    AumOSAPIError,
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)

# HTTP status code → (exception_class, is_retryable, retry_after_hint_seconds)
_HTTP_STATUS_MAP: dict[int, tuple[type[AumOSAPIError], bool, int | None]] = {
    400: (ValidationError, False, None),
    401: (AuthenticationError, False, None),
    403: (PermissionError, False, None),
    404: (NotFoundError, False, None),
    408: (TimeoutError, True, 5),
    409: (AumOSAPIError, False, None),  # Conflict — context-dependent
    422: (ValidationError, False, None),
    429: (RateLimitError, True, 60),
    500: (ServerError, True, 10),
    502: (ServerError, True, 5),
    503: (ServerError, True, 30),
    504: (ServerError, True, 15),
}

# Platform error code prefixes for AumOS-specific errors
_PLATFORM_ERROR_PREFIX: str = "AUMOS_"

# Per-error-code documentation snippets for SDK error docs
_ERROR_DOCS: dict[str, str] = {
    "AUMOS_AUTH_EXPIRED": (
        "Your API key or bearer token has expired. Rotate your key in the AumOS console "
        "at https://console.aumos.ai/settings/api-keys and update your SDK configuration."
    ),
    "AUMOS_QUOTA_EXCEEDED": (
        "Your tenant has exceeded the configured API quota. Check your plan limits "
        "in the billing dashboard or contact support to upgrade."
    ),
    "AUMOS_TENANT_SUSPENDED": (
        "Your tenant account has been suspended. Contact support@aumos.ai "
        "to resolve the suspension before retrying."
    ),
    "AUMOS_MODEL_NOT_FOUND": (
        "The requested model ID does not exist in your tenant's model registry. "
        "Use GET /api/v1/models to list available model IDs."
    ),
    "AUMOS_GENERATION_FAILED": (
        "The synthetic data generation job failed. Check the job logs via "
        "GET /api/v1/runs/{run_id}/logs for detailed error information."
    ),
    "AUMOS_SCHEMA_INVALID": (
        "The provided dataset schema is invalid. Verify that all column types are "
        "supported (string, integer, float, boolean, datetime, categorical) and that "
        "categorical columns include a non-empty 'categories' list."
    ),
    "AUMOS_PRIVACY_BUDGET_EXCEEDED": (
        "The requested epsilon value exceeds your tenant's configured privacy budget. "
        "Reduce the epsilon value or contact your compliance team to adjust the budget."
    ),
    "AUMOS_RATE_LIMITED": (
        "Too many requests in a short window. The SDK will automatically retry with "
        "exponential backoff. Reduce request concurrency if this occurs frequently."
    ),
    "AUMOS_INTERNAL_ERROR": (
        "An unexpected internal error occurred. This is a platform-side issue. "
        "Retry after a brief delay. If the problem persists, contact support@aumos.ai "
        "with the request_id from the error response."
    ),
}

# Cross-language error class name mappings
_LANGUAGE_ERROR_NAMES: dict[str, dict[str, str]] = {
    "python": {
        "base": "AumOSError",
        "api": "AumOSAPIError",
        "auth": "AuthenticationError",
        "permission": "PermissionError",
        "not_found": "NotFoundError",
        "validation": "ValidationError",
        "rate_limit": "RateLimitError",
        "server": "ServerError",
        "timeout": "TimeoutError",
        "connection": "ConnectionError",
    },
    "typescript": {
        "base": "AumOSError",
        "api": "AumOSAPIError",
        "auth": "AuthenticationError",
        "permission": "PermissionError",
        "not_found": "NotFoundError",
        "validation": "ValidationError",
        "rate_limit": "RateLimitError",
        "server": "ServerError",
        "timeout": "TimeoutError",
        "connection": "ConnectionError",
    },
    "go": {
        "base": "error",
        "api": "*APIError",
        "auth": "*AuthenticationError",
        "permission": "*PermissionError",
        "not_found": "*NotFoundError",
        "validation": "*ValidationError",
        "rate_limit": "*RateLimitError",
        "server": "*ServerError",
        "timeout": "*TimeoutError",
        "connection": "*ConnectionError",
    },
    "java": {
        "base": "AumOSException",
        "api": "AumOSAPIException",
        "auth": "AuthenticationException",
        "permission": "PermissionException",
        "not_found": "NotFoundException",
        "validation": "ValidationException",
        "rate_limit": "RateLimitException",
        "server": "ServerException",
        "timeout": "TimeoutException",
        "connection": "ConnectionException",
    },
}


class ErrorUnifier:
    """Maps AumOS platform errors to SDK exception types across all languages.

    Provides HTTP status code classification, retry hint extraction, platform
    error code documentation lookup, and cross-language error name resolution
    to ensure consistent error handling documentation and behavior.
    """

    def classify_http_error(self, status_code: int) -> dict[str, Any]:
        """Classify an HTTP status code into an SDK exception and retry metadata.

        Args:
            status_code: HTTP response status code.

        Returns:
            Classification dict with exception_class_name, is_retryable,
            retry_after_seconds, and description.
        """
        entry = _HTTP_STATUS_MAP.get(status_code)

        if entry is None:
            if 400 <= status_code < 500:
                return {
                    "exception_class_name": "AumOSAPIError",
                    "status_code": status_code,
                    "is_retryable": False,
                    "retry_after_seconds": None,
                    "description": f"Client error {status_code}. Fix the request before retrying.",
                }
            if 500 <= status_code < 600:
                return {
                    "exception_class_name": "ServerError",
                    "status_code": status_code,
                    "is_retryable": True,
                    "retry_after_seconds": 10,
                    "description": f"Server error {status_code}. Safe to retry with backoff.",
                }
            return {
                "exception_class_name": "AumOSAPIError",
                "status_code": status_code,
                "is_retryable": False,
                "retry_after_seconds": None,
                "description": f"Unexpected status {status_code}.",
            }

        exception_class, is_retryable, retry_after = entry
        return {
            "exception_class_name": exception_class.__name__,
            "status_code": status_code,
            "is_retryable": is_retryable,
            "retry_after_seconds": retry_after,
            "description": self._describe_status(status_code),
        }

    def raise_for_response(
        self,
        status_code: int,
        response_body: dict[str, Any] | str | None = None,
        request_id: str | None = None,
    ) -> None:
        """Raise the appropriate SDK exception for a failed HTTP response.

        Args:
            status_code: HTTP response status code.
            response_body: Optional parsed response body or raw string.
            request_id: Optional request identifier for support tracing.

        Raises:
            AumOSAPIError or a subclass for any status >= 400.
        """
        if status_code < 400:
            return

        message = self._extract_error_message(response_body)
        error_code = self._extract_platform_error_code(response_body)

        classification = self.classify_http_error(status_code)
        exception_name = classification["exception_class_name"]

        exception_class_map: dict[str, type[AumOSAPIError]] = {
            "AumOSAPIError": AumOSAPIError,
            "AuthenticationError": AuthenticationError,
            "PermissionError": PermissionError,
            "NotFoundError": NotFoundError,
            "ValidationError": ValidationError,
            "RateLimitError": RateLimitError,
            "ServerError": ServerError,
            "TimeoutError": TimeoutError,
        }

        exception_class = exception_class_map.get(exception_name, AumOSAPIError)
        raise exception_class(
            message=message,
            status_code=status_code,
            error_code=error_code,
            request_id=request_id,
        )

    def get_error_documentation(self, platform_error_code: str) -> dict[str, Any]:
        """Return documentation for a platform-specific AumOS error code.

        Args:
            platform_error_code: AumOS platform error code (e.g., AUMOS_QUOTA_EXCEEDED).

        Returns:
            Documentation dict with explanation and remediation steps.
        """
        normalized = platform_error_code.upper()
        if not normalized.startswith(_PLATFORM_ERROR_PREFIX):
            normalized = f"{_PLATFORM_ERROR_PREFIX}{normalized}"

        doc = _ERROR_DOCS.get(normalized)
        if doc is None:
            return {
                "error_code": normalized,
                "documented": False,
                "explanation": f"No documentation available for error code '{normalized}'.",
                "remediation": "Contact support@aumos.ai with the request_id from the error response.",
            }

        return {
            "error_code": normalized,
            "documented": True,
            "explanation": doc,
            "remediation": doc,
        }

    def resolve_error_name(self, error_type: str, language: str) -> str:
        """Resolve the SDK error class name for a given error type and language.

        Args:
            error_type: Canonical error type key (e.g., 'auth', 'rate_limit').
            language: Target language (python | typescript | go | java).

        Returns:
            Language-specific error class name string.

        Raises:
            ValueError: If language or error_type is not supported.
        """
        if language not in _LANGUAGE_ERROR_NAMES:
            raise ValueError(
                f"Unsupported language '{language}'. Supported: {sorted(_LANGUAGE_ERROR_NAMES)}"
            )
        lang_map = _LANGUAGE_ERROR_NAMES[language]
        if error_type not in lang_map:
            raise ValueError(
                f"Unknown error type '{error_type}'. Available: {sorted(lang_map)}"
            )
        return lang_map[error_type]

    def get_all_error_names(self, language: str) -> dict[str, str]:
        """Return the full error name mapping for a target language.

        Args:
            language: Target language (python | typescript | go | java).

        Returns:
            Dict mapping canonical error type to language-specific class name.

        Raises:
            ValueError: If language is not supported.
        """
        if language not in _LANGUAGE_ERROR_NAMES:
            raise ValueError(
                f"Unsupported language '{language}'. Supported: {sorted(_LANGUAGE_ERROR_NAMES)}"
            )
        return dict(_LANGUAGE_ERROR_NAMES[language])

    def generate_error_reference(self) -> dict[str, Any]:
        """Generate a complete error code reference document.

        Returns:
            Reference dict with all documented error codes, HTTP status mappings,
            and per-language exception hierarchy.
        """
        http_status_entries = []
        for status_code in sorted(_HTTP_STATUS_MAP):
            classification = self.classify_http_error(status_code)
            http_status_entries.append(classification)

        platform_errors = []
        for code, doc in sorted(_ERROR_DOCS.items()):
            platform_errors.append({
                "error_code": code,
                "explanation": doc,
            })

        return {
            "http_status_mappings": http_status_entries,
            "platform_error_codes": platform_errors,
            "language_error_names": _LANGUAGE_ERROR_NAMES,
            "total_http_mappings": len(_HTTP_STATUS_MAP),
            "total_platform_codes": len(_ERROR_DOCS),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_error_message(self, body: dict[str, Any] | str | None) -> str:
        """Extract a human-readable error message from a response body.

        Args:
            body: Parsed response body or raw string.

        Returns:
            Error message string.
        """
        if body is None:
            return "An unexpected error occurred."
        if isinstance(body, str):
            return body or "An unexpected error occurred."
        return (
            body.get("message")
            or body.get("detail")
            or body.get("error")
            or "An unexpected error occurred."
        )

    def _extract_platform_error_code(self, body: dict[str, Any] | str | None) -> str | None:
        """Extract the AumOS platform error code from a response body.

        Args:
            body: Parsed response body.

        Returns:
            Platform error code string or None if not present.
        """
        if not isinstance(body, dict):
            return None
        return body.get("error_code") or body.get("code") or None

    def _describe_status(self, status_code: int) -> str:
        """Return a human-readable description for a known HTTP status code.

        Args:
            status_code: HTTP status code.

        Returns:
            Description string.
        """
        descriptions: dict[int, str] = {
            400: "Bad request — the request body or parameters are invalid.",
            401: "Unauthorized — API key or bearer token is missing or invalid.",
            403: "Forbidden — you lack permission for this resource.",
            404: "Not found — the requested resource does not exist.",
            408: "Request timeout — the server did not receive a complete request in time.",
            409: "Conflict — the resource is in a conflicting state.",
            422: "Unprocessable entity — semantic validation failed.",
            429: "Too many requests — rate limit exceeded. Retry after backoff.",
            500: "Internal server error — an unexpected error occurred on the platform.",
            502: "Bad gateway — upstream service unavailable.",
            503: "Service unavailable — the platform is temporarily offline.",
            504: "Gateway timeout — upstream service did not respond in time.",
        }
        return descriptions.get(status_code, f"HTTP {status_code} error.")
