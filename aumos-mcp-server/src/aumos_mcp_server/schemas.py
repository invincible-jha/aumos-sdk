"""Pydantic input models for all MCP tool arguments.

These models provide validation before passing arguments to the AumOS SDK client.
Extra fields are forbidden so typos are caught early rather than silently ignored.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    """Base model with extra='forbid' to catch parameter typos early."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Agent tool inputs
# ---------------------------------------------------------------------------


class AgentCreateInput(_StrictModel):
    """Input for agents.create tool."""

    name: str = Field(..., description="Human-readable name for the agent")
    model: str = Field(..., description="Model identifier from the AumOS model registry")
    instructions: str = Field(..., description="System prompt instructions for the agent")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Optional key-value metadata")


class AgentGetInput(_StrictModel):
    """Input for agents.get tool."""

    agent_id: str = Field(..., description="UUID of the agent to retrieve")


class AgentListInput(_StrictModel):
    """Input for agents.list tool."""

    page_size: int = Field(default=20, ge=1, le=100, description="Number of results per page")
    page_token: Optional[str] = Field(default=None, description="Pagination token")


# ---------------------------------------------------------------------------
# Run tool inputs
# ---------------------------------------------------------------------------


class RunCreateInput(_StrictModel):
    """Input for runs.create tool."""

    agent_id: str = Field(..., description="UUID of the agent to run")
    thread_id: Optional[str] = Field(default=None, description="Existing thread UUID, or None to create a new thread")
    input_text: str = Field(..., description="User message to send to the agent")


class RunGetInput(_StrictModel):
    """Input for runs.get tool."""

    run_id: str = Field(..., description="UUID of the run to retrieve")


class RunCancelInput(_StrictModel):
    """Input for runs.cancel tool."""

    run_id: str = Field(..., description="UUID of the run to cancel")


# ---------------------------------------------------------------------------
# Model tool inputs
# ---------------------------------------------------------------------------


class ModelRegisterInput(_StrictModel):
    """Input for models.register tool."""

    name: str = Field(..., description="Model display name")
    provider: str = Field(..., description="Model provider (e.g., 'anthropic', 'openai')")
    model_id: str = Field(..., description="Provider-specific model identifier")
    capabilities: list[str] = Field(default_factory=list, description="Capability tags")


class ModelGetInput(_StrictModel):
    """Input for models.get tool."""

    model_id: str = Field(..., description="AumOS model registry UUID")


# ---------------------------------------------------------------------------
# Governance tool inputs
# ---------------------------------------------------------------------------


class PolicyCheckInput(_StrictModel):
    """Input for governance.policy_check tool."""

    policy_id: str = Field(..., description="UUID of the policy to evaluate")
    resource_type: str = Field(..., description="Type of resource being checked")
    resource_id: str = Field(..., description="UUID of the resource to check")
    action: str = Field(..., description="Proposed action (e.g., 'generate', 'export')")


class GovernanceReportInput(_StrictModel):
    """Input for governance.report tool."""

    start_date: str = Field(..., description="ISO 8601 start date (e.g., '2025-01-01')")
    end_date: str = Field(..., description="ISO 8601 end date")
    policy_ids: Optional[list[str]] = Field(default=None, description="Filter by specific policy UUIDs")


# ---------------------------------------------------------------------------
# Data tool inputs
# ---------------------------------------------------------------------------


class DataGenerateInput(_StrictModel):
    """Input for data.generate tool."""

    schema: dict[str, Any] = Field(..., description="Schema definition with column names and types")
    rows: int = Field(..., ge=1, le=100_000, description="Number of synthetic rows to generate")
    privacy_epsilon: float = Field(default=1.0, gt=0.0, description="Differential privacy epsilon")
    modality: str = Field(default="tabular", description="Data modality: tabular, text, image")


class DataPreviewInput(_StrictModel):
    """Input for data.preview tool — generates a small sample for inspection."""

    schema: dict[str, Any] = Field(..., description="Schema definition")
    preview_rows: int = Field(default=5, ge=1, le=20, description="Number of preview rows")


# ---------------------------------------------------------------------------
# Benchmark tool inputs
# ---------------------------------------------------------------------------


class BenchmarkRunInput(_StrictModel):
    """Input for benchmarks.run tool."""

    config_name: str = Field(..., description="Benchmark configuration name from the benchmark registry")
    dataset_name: Optional[str] = Field(default=None, description="Reference dataset to use")


class BenchmarkGetResultsInput(_StrictModel):
    """Input for benchmarks.get_results tool."""

    run_id: str = Field(..., description="UUID of the benchmark run")
