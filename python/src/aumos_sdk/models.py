# Copyright 2026 AumOS Enterprise
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Pydantic models for the AumOS API response types.

All field names use snake_case in Python but are serialized to camelCase
for the wire format (API JSON) via the model's ``model_config``.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(string: str) -> str:
    components = string.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


class _AumOSBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="allow",
    )


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    ERROR = "error"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ToolType(str, Enum):
    FUNCTION = "function"
    RETRIEVAL = "retrieval"
    CODE_INTERPRETER = "code_interpreter"
    HTTP = "http"


class PolicyType(str, Enum):
    CONTENT_FILTER = "content_filter"
    RATE_LIMIT = "rate_limit"
    DATA_GOVERNANCE = "data_governance"
    ACCESS_CONTROL = "access_control"


class AuditOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Component models
# ---------------------------------------------------------------------------


class AgentTool(_AumOSBase):
    """A tool available to an agent during execution."""

    name: str
    type: ToolType
    description: str | None = None
    parameters: dict[str, Any] | None = None


class TokenUsage(_AumOSBase):
    """Token consumption for a single run."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


# ---------------------------------------------------------------------------
# Core resource models
# ---------------------------------------------------------------------------


class Agent(_AumOSBase):
    """An AI agent registered in AumOS.

    Agents encapsulate a model, system prompt, tools, and configuration.
    They are the primary unit of work in the AumOS platform.
    """

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None = None
    status: AgentStatus
    model_id: str
    system_prompt: str | None = None
    tools: list[AgentTool] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @property
    def is_active(self) -> bool:
        return self.status == AgentStatus.ACTIVE


class Run(_AumOSBase):
    """A single execution run of an agent.

    Runs are created by calling :meth:`~aumos_sdk.AgentsResource.create_run`
    and transition through: ``queued`` → ``running`` → ``completed`` (or
    ``failed`` / ``cancelled`` / ``timeout``).
    """

    id: UUID
    agent_id: UUID
    tenant_id: UUID
    status: RunStatus
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    error: str | None = None
    usage: TokenUsage | None = None
    duration_ms: int | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.TIMEOUT,
        }

    @property
    def succeeded(self) -> bool:
        return self.status == RunStatus.COMPLETED


class Model(_AumOSBase):
    """A model available through the AumOS model registry."""

    id: str
    name: str
    provider: str
    description: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    context_window: int | None = None
    max_output_tokens: int | None = None
    deprecated: bool = False


class Policy(_AumOSBase):
    """A governance policy applied to agent executions."""

    id: UUID
    name: str
    type: PolicyType
    enabled: bool
    rules: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None


class AuditLogEntry(_AumOSBase):
    """A single entry in the platform audit log."""

    id: UUID
    tenant_id: UUID
    action: str
    actor_id: str
    resource_type: str | None = None
    resource_id: str | None = None
    outcome: AuditOutcome | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class HealthResponse(_AumOSBase):
    """Platform health check response."""

    status: str
    version: str
    timestamp: datetime
    components: dict[str, str] = Field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"


# ---------------------------------------------------------------------------
# List (paginated) responses
# ---------------------------------------------------------------------------


class AgentListResponse(_AumOSBase):
    """Paginated list of agents."""

    items: list[Agent]
    total: int
    next_page_token: str | None = None


class RunListResponse(_AumOSBase):
    """Paginated list of runs."""

    items: list[Run]
    total: int
    next_page_token: str | None = None


class ModelListResponse(_AumOSBase):
    """List of available models."""

    items: list[Model]
    next_page_token: str | None = None


class PolicyListResponse(_AumOSBase):
    """List of governance policies."""

    items: list[Policy]


class AuditLogListResponse(_AumOSBase):
    """Paginated list of audit log entries."""

    items: list[AuditLogEntry]
    total: int
    next_page_token: str | None = None


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateAgentRequest(_AumOSBase):
    """Request body for creating a new agent."""

    name: str
    model_id: str
    description: str | None = None
    system_prompt: str | None = None
    tools: list[AgentTool] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateAgentRequest(_AumOSBase):
    """Request body for partially updating an agent."""

    name: str | None = None
    description: str | None = None
    status: AgentStatus | None = None
    system_prompt: str | None = None
    tools: list[AgentTool] | None = None
    metadata: dict[str, Any] | None = None


class CreateRunRequest(_AumOSBase):
    """Request body for starting an agent run."""

    input: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
