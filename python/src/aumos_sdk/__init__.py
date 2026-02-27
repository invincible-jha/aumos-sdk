# Copyright 2026 AumOS Enterprise
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""AumOS Enterprise Python SDK.

The AumOS SDK provides idiomatic async Python access to the AumOS
Enterprise platform APIs.

Quick start::

    import asyncio
    from aumos_sdk import AumOSClient

    async def main():
        async with AumOSClient(api_key="sk-aumos-...") as client:
            # Create an agent
            agent = await client.agents.create(
                name="my-agent",
                model_id="aumos:claude-opus-4-6",
                system_prompt="You are a helpful assistant.",
            )

            # Run it
            run = await client.agents.create_run(
                agent_id=agent.id,
                input={"message": "Hello!"},
            )

            # Wait for completion
            completed_run = await client.agents.wait_for_run(
                agent.id, run.id
            )
            print(completed_run.output)

    asyncio.run(main())
"""

from .auth import ApiKeyAuth, AuthStrategy, BearerTokenAuth, create_auth_strategy
from .client import AumOSClient, AgentsResource, GovernanceResource, ModelsResource, RunsResource
from .error_unifier import ErrorUnifier
from .go_client import GoClientGenerator
from .integration_guide import IntegrationGuideGenerator
from .java_client import JavaClientGenerator
from .openapi_codegen import OpenAPICodegen
from .python_async_client import PythonAsyncClientGenerator
from .typescript_client import TypeScriptClientGenerator
from .exceptions import (
    AumOSAPIError,
    AumOSError,
    AuthenticationError,
    ConfigurationError,
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
    AgentStatus,
    AgentTool,
    AuditLogEntry,
    AuditLogListResponse,
    AuditOutcome,
    CreateAgentRequest,
    CreateRunRequest,
    HealthResponse,
    Model,
    ModelListResponse,
    Policy,
    PolicyListResponse,
    PolicyType,
    Run,
    RunListResponse,
    RunStatus,
    TokenUsage,
    ToolType,
    UpdateAgentRequest,
)

__version__ = "1.0.0"
__all__ = [
    # Client
    "AumOSClient",
    "AgentsResource",
    "GovernanceResource",
    "ModelsResource",
    "RunsResource",
    # Auth
    "ApiKeyAuth",
    "AuthStrategy",
    "BearerTokenAuth",
    "create_auth_strategy",
    # Exceptions
    "AumOSError",
    "AumOSAPIError",
    "AuthenticationError",
    "ConfigurationError",
    "ConnectionError",
    "NotFoundError",
    "PermissionError",
    "RateLimitError",
    "ServerError",
    "TimeoutError",
    "ValidationError",
    # Models — enums
    "AgentStatus",
    "AuditOutcome",
    "PolicyType",
    "RunStatus",
    "ToolType",
    # Models — resources
    "Agent",
    "AgentTool",
    "AuditLogEntry",
    "HealthResponse",
    "Model",
    "Policy",
    "Run",
    "TokenUsage",
    # Models — list responses
    "AgentListResponse",
    "AuditLogListResponse",
    "ModelListResponse",
    "PolicyListResponse",
    "RunListResponse",
    # Models — requests
    "CreateAgentRequest",
    "CreateRunRequest",
    "UpdateAgentRequest",
    # SDK tooling
    "ErrorUnifier",
    "GoClientGenerator",
    "IntegrationGuideGenerator",
    "JavaClientGenerator",
    "OpenAPICodegen",
    "PythonAsyncClientGenerator",
    "TypeScriptClientGenerator",
]
