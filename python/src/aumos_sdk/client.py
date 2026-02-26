# Copyright 2026 AumOS Enterprise
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""AumOS Python SDK — async HTTP client.

The :class:`AumOSClient` is the primary entry point. Construct it once,
share it across your application, and call ``await client.aclose()``
(or use it as an async context manager) when you are done.

Usage::

    from aumos_sdk import AumOSClient

    async with AumOSClient(api_key="sk-aumos-...") as client:
        agent = await client.agents.create(
            name="support-bot",
            model_id="aumos:claude-opus-4-6",
            system_prompt="You are a helpful enterprise support assistant.",
        )
        run = await client.agents.create_run(
            agent_id=agent.id,
            input={"message": "How do I reset my password?"},
        )
        print(run.status)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

import httpx

from .auth import AuthStrategy, BearerTokenAuth, create_auth_strategy
from .exceptions import (
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
from .models import (
    Agent,
    AgentListResponse,
    AgentTool,
    AgentStatus,
    AuditLogListResponse,
    CreateAgentRequest,
    CreateRunRequest,
    HealthResponse,
    Model,
    ModelListResponse,
    Policy,
    PolicyListResponse,
    Run,
    RunListResponse,
    UpdateAgentRequest,
)

logger = logging.getLogger("aumos_sdk")

_DEFAULT_BASE_URL = "https://api.aumos.io/v1"
_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_MAX_RETRIES = 3
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class _Resource:
    """Base class for API resource namespaces."""

    def __init__(self, client: AumOSClient) -> None:
        self._client = client


class AgentsResource(_Resource):
    """Operations on :class:`~aumos_sdk.models.Agent` resources.

    Access via ``client.agents``.
    """

    async def list(
        self,
        *,
        status: AgentStatus | None = None,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> AgentListResponse:
        """List agents in the current tenant.

        Args:
            status: Optional status filter.
            page_size: Number of results per page (1–100).
            page_token: Opaque token from a previous response for pagination.

        Returns:
            :class:`~aumos_sdk.models.AgentListResponse` with ``items`` and
            optional ``next_page_token``.
        """
        params: dict[str, Any] = {"pageSize": page_size}
        if status is not None:
            params["status"] = status.value
        if page_token is not None:
            params["pageToken"] = page_token

        data = await self._client._get("/agents", params=params)
        return AgentListResponse.model_validate(data)

    async def create(
        self,
        *,
        name: str,
        model_id: str,
        description: str | None = None,
        system_prompt: str | None = None,
        tools: list[AgentTool] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Agent:
        """Create a new agent.

        Args:
            name: Human-readable agent name (max 255 chars).
            model_id: Model identifier (e.g., ``"aumos:claude-opus-4-6"``).
            description: Optional long-form description.
            system_prompt: Instructions injected at the start of every run.
            tools: List of tools available to the agent.
            metadata: Arbitrary key-value pairs for application use.

        Returns:
            The newly created :class:`~aumos_sdk.models.Agent`.
        """
        request = CreateAgentRequest(
            name=name,
            model_id=model_id,
            description=description,
            system_prompt=system_prompt,
            tools=tools or [],
            metadata=metadata or {},
        )
        data = await self._client._post(
            "/agents",
            body=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Agent.model_validate(data)

    async def get(self, agent_id: UUID | str) -> Agent:
        """Retrieve a single agent by ID.

        Args:
            agent_id: The agent UUID.

        Returns:
            The :class:`~aumos_sdk.models.Agent`.

        Raises:
            NotFoundError: If no agent exists with the given ID.
        """
        data = await self._client._get(f"/agents/{agent_id}")
        return Agent.model_validate(data)

    async def update(
        self,
        agent_id: UUID | str,
        *,
        name: str | None = None,
        description: str | None = None,
        status: AgentStatus | None = None,
        system_prompt: str | None = None,
        tools: list[AgentTool] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Agent:
        """Partially update an agent.

        Only provided fields are modified; omitted fields remain unchanged.

        Returns:
            The updated :class:`~aumos_sdk.models.Agent`.
        """
        request = UpdateAgentRequest(
            name=name,
            description=description,
            status=status,
            system_prompt=system_prompt,
            tools=tools,
            metadata=metadata,
        )
        data = await self._client._patch(
            f"/agents/{agent_id}",
            body=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Agent.model_validate(data)

    async def delete(self, agent_id: UUID | str) -> None:
        """Delete an agent.

        This is a soft delete — the agent enters ``archived`` status and
        is fully purged after 30 days.

        Raises:
            NotFoundError: If no agent exists with the given ID.
        """
        await self._client._delete(f"/agents/{agent_id}")

    async def create_run(
        self,
        agent_id: UUID | str,
        *,
        input: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        timeout_seconds: int = 300,
    ) -> Run:
        """Start a new run for the given agent.

        The run is accepted asynchronously — poll :meth:`RunsResource.get`
        until ``run.is_terminal`` is True, or use :meth:`wait_for_run`.

        Args:
            agent_id: The agent to execute.
            input: Structured input payload (e.g., ``{"message": "..."}``) .
            metadata: Optional metadata attached to this run.
            timeout_seconds: Server-side execution timeout (1–3600 seconds).

        Returns:
            A :class:`~aumos_sdk.models.Run` in ``queued`` or ``running`` status.
        """
        request = CreateRunRequest(
            input=input,
            metadata=metadata or {},
            timeout_seconds=timeout_seconds,
        )
        data = await self._client._post(
            f"/agents/{agent_id}/runs",
            body=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Run.model_validate(data)

    async def list_runs(
        self,
        agent_id: UUID | str,
        *,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> RunListResponse:
        """List runs for a specific agent."""
        params: dict[str, Any] = {"pageSize": page_size}
        if page_token is not None:
            params["pageToken"] = page_token

        data = await self._client._get(f"/agents/{agent_id}/runs", params=params)
        return RunListResponse.model_validate(data)

    async def wait_for_run(
        self,
        agent_id: UUID | str,
        run_id: UUID | str,
        *,
        poll_interval_seconds: float = 2.0,
        max_wait_seconds: float = 300.0,
    ) -> Run:
        """Poll a run until it reaches a terminal status.

        Args:
            agent_id: The owning agent's ID.
            run_id: The run to poll.
            poll_interval_seconds: Seconds between status checks.
            max_wait_seconds: Maximum time to wait before raising TimeoutError.

        Returns:
            The :class:`~aumos_sdk.models.Run` once it reaches a terminal state.

        Raises:
            TimeoutError: If the run does not complete within ``max_wait_seconds``.
        """
        elapsed = 0.0
        while elapsed < max_wait_seconds:
            run = await self._client.runs.get(run_id)
            if run.is_terminal:
                return run
            await asyncio.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds

        raise TimeoutError(
            f"Run {run_id} did not complete within {max_wait_seconds} seconds."
        )


class RunsResource(_Resource):
    """Operations on :class:`~aumos_sdk.models.Run` resources.

    Access via ``client.runs``.
    """

    async def get(self, run_id: UUID | str) -> Run:
        """Retrieve a run by ID.

        Args:
            run_id: The run UUID.

        Returns:
            The :class:`~aumos_sdk.models.Run`.

        Raises:
            NotFoundError: If no run exists with the given ID.
        """
        data = await self._client._get(f"/runs/{run_id}")
        return Run.model_validate(data)


class ModelsResource(_Resource):
    """Operations on model registry resources.

    Access via ``client.models``.
    """

    async def list(
        self,
        *,
        provider: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> ModelListResponse:
        """List models available to the tenant.

        Args:
            provider: Filter by provider name (e.g., ``"anthropic"``).
            page_size: Number of results per page.
            page_token: Pagination token from a previous response.

        Returns:
            :class:`~aumos_sdk.models.ModelListResponse`.
        """
        params: dict[str, Any] = {"pageSize": page_size}
        if provider is not None:
            params["provider"] = provider
        if page_token is not None:
            params["pageToken"] = page_token

        data = await self._client._get("/models", params=params)
        return ModelListResponse.model_validate(data)

    async def get(self, model_id: str) -> Model:
        """Retrieve a model by ID.

        Args:
            model_id: The model identifier.

        Returns:
            The :class:`~aumos_sdk.models.Model`.

        Raises:
            NotFoundError: If the model ID is not available.
        """
        data = await self._client._get(f"/models/{model_id}")
        return Model.model_validate(data)


class GovernanceResource(_Resource):
    """Governance policy and audit log operations.

    Access via ``client.governance``.
    """

    async def list_policies(self) -> PolicyListResponse:
        """List all governance policies for the tenant."""
        data = await self._client._get("/governance/policies")
        return PolicyListResponse.model_validate(data)

    async def list_audit_logs(
        self,
        *,
        page_size: int = 50,
        page_token: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        action: str | None = None,
    ) -> AuditLogListResponse:
        """Retrieve audit log entries with optional filters.

        Args:
            page_size: Number of entries per page.
            page_token: Pagination token.
            start_time: ISO-8601 timestamp lower bound.
            end_time: ISO-8601 timestamp upper bound.
            action: Filter by action type string.

        Returns:
            :class:`~aumos_sdk.models.AuditLogListResponse`.
        """
        params: dict[str, Any] = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if action:
            params["action"] = action

        data = await self._client._get("/governance/audit-logs", params=params)
        return AuditLogListResponse.model_validate(data)


class AumOSClient:
    """Async HTTP client for the AumOS Enterprise API.

    Instantiate once and reuse across your application. The client manages
    connection pooling, authentication, automatic retries with exponential
    backoff, and optional bearer-token refresh.

    Args:
        api_key: API key for authentication. If omitted, reads from the
            ``AUMOS_API_KEY`` environment variable.
        token: Bearer token (alternative to api_key).
        expires_at: Unix timestamp for bearer token expiry.
        base_url: Override the default API base URL.
        timeout: Request timeout in seconds. Defaults to 30.
        max_retries: Number of retries for transient errors. Defaults to 3.

    Example::

        # Context manager (preferred)
        async with AumOSClient(api_key="sk-aumos-...") as client:
            health = await client.health()
            print(health.status)

        # Manual lifecycle
        client = AumOSClient()
        try:
            agents = await client.agents.list()
        finally:
            await client.aclose()
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        token: str | None = None,
        expires_at: float | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        self._auth = create_auth_strategy(
            api_key=api_key,
            token=token,
            expires_at=expires_at,
        )
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries

        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "aumos-python-sdk/1.0.0",
            },
        )

        # Resource namespaces
        self.agents = AgentsResource(self)
        self.runs = RunsResource(self)
        self.models = ModelsResource(self)
        self.governance = GovernanceResource(self)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()

    async def __aenter__(self) -> "AumOSClient":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # High-level convenience
    # ------------------------------------------------------------------

    async def health(self) -> HealthResponse:
        """Check platform health.

        This endpoint does not require authentication and is suitable
        for readiness probes.

        Returns:
            :class:`~aumos_sdk.models.HealthResponse`.
        """
        data = await self._request("GET", "/health", authenticated=False)
        return HealthResponse.model_validate(data)

    # ------------------------------------------------------------------
    # Internal HTTP primitives
    # ------------------------------------------------------------------

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def _post(
        self,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", path, json=body)

    async def _patch(
        self,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request("PATCH", path, json=body)

    async def _delete(self, path: str) -> None:
        await self._request("DELETE", path, expect_body=False)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        authenticated: bool = True,
        expect_body: bool = True,
    ) -> dict[str, Any]:
        """Execute an HTTP request with retry logic and error mapping.

        Args:
            method: HTTP verb (GET, POST, PATCH, DELETE).
            path: URL path relative to the base URL.
            params: Query parameters.
            json: Request body (serialized to JSON).
            authenticated: Whether to attach authentication headers.
            expect_body: Whether to parse and return the response body.

        Returns:
            Parsed JSON response body (or empty dict for no-body responses).

        Raises:
            AuthenticationError: 401 response.
            PermissionError: 403 response.
            NotFoundError: 404 response.
            ValidationError: 422 response.
            RateLimitError: 429 response.
            ServerError: 5xx response.
            TimeoutError: Request timed out.
            ConnectionError: Network error.
        """
        if authenticated and isinstance(self._auth, BearerTokenAuth):
            if self._auth.needs_refresh():
                refresher = self._auth.get_refresher()
                if refresher is not None:
                    new_token, new_expiry = refresher()
                    self._auth.update_token(new_token, new_expiry)

        headers: dict[str, str] = {}
        if authenticated:
            headers.update(self._auth.get_headers())

        last_exception: Exception | None = None

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                backoff = min(2 ** (attempt - 1), 30)
                logger.debug("Retry attempt %d after %.1f seconds", attempt, backoff)
                await asyncio.sleep(backoff)

            try:
                response = await self._http.request(
                    method,
                    path,
                    params=params,
                    json=json,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                last_exception = TimeoutError(
                    f"Request timed out after {self._timeout}s: {method} {path}"
                )
                logger.warning("Request timeout on attempt %d: %s", attempt + 1, exc)
                continue
            except httpx.ConnectError as exc:
                raise ConnectionError(
                    f"Unable to connect to AumOS API at {self._base_url}: {exc}"
                ) from exc
            except httpx.RequestError as exc:
                raise ConnectionError(
                    f"Network error during {method} {path}: {exc}"
                ) from exc

            request_id = response.headers.get("X-Request-ID")

            if response.status_code < 400:
                if not expect_body or response.status_code == 204:
                    return {}
                return response.json()

            # Error response — parse body if possible
            try:
                error_body: dict[str, Any] = response.json()
            except Exception:
                error_body = {}

            error_message = error_body.get("message", response.reason_phrase)
            error_code = error_body.get("error")
            details = error_body.get("details")

            status_code = response.status_code

            if status_code == 401:
                raise AuthenticationError(
                    error_message,
                    status_code=status_code,
                    error_code=error_code,
                    details=details,
                    request_id=request_id,
                )
            if status_code == 403:
                raise PermissionError(
                    error_message,
                    status_code=status_code,
                    error_code=error_code,
                    details=details,
                    request_id=request_id,
                )
            if status_code == 404:
                raise NotFoundError(
                    error_message,
                    status_code=status_code,
                    error_code=error_code,
                    details=details,
                    request_id=request_id,
                )
            if status_code == 422:
                raise ValidationError(
                    error_message,
                    status_code=status_code,
                    error_code=error_code,
                    details=details,
                    request_id=request_id,
                )
            if status_code == 429:
                retry_after: float | None = None
                raw_retry = response.headers.get("Retry-After")
                if raw_retry:
                    try:
                        retry_after = float(raw_retry)
                    except ValueError:
                        pass

                last_exception = RateLimitError(
                    error_message,
                    status_code=status_code,
                    error_code=error_code,
                    details=details,
                    request_id=request_id,
                    retry_after=retry_after,
                )
                if attempt < self._max_retries:
                    wait = retry_after or (2 ** attempt)
                    logger.warning("Rate limited. Retrying after %.1f seconds.", wait)
                    await asyncio.sleep(wait)
                    continue
                raise last_exception  # type: ignore[misc]

            if status_code >= 500:
                last_exception = ServerError(
                    error_message,
                    status_code=status_code,
                    error_code=error_code,
                    details=details,
                    request_id=request_id,
                )
                logger.warning("Server error %d on attempt %d", status_code, attempt + 1)
                continue

            raise AumOSAPIError(
                error_message,
                status_code=status_code,
                error_code=error_code,
                details=details,
                request_id=request_id,
            )

        raise last_exception or AumOSAPIError(
            f"Request failed after {self._max_retries} retries: {method} {path}",
            status_code=0,
        )

    def __repr__(self) -> str:
        return f"AumOSClient(base_url={self._base_url!r}, auth={self._auth!r})"
