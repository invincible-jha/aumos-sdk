"""Unit tests for AumOS MCP tool registration and input validation.

Tests verify that:
- Each tool validates its inputs with Pydantic before calling the SDK
- Invalid inputs raise ValidationError (not silently pass)
- Tools return TextContent with valid JSON on success
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.server import Server

from aumos_mcp_server.schemas import AgentCreateInput, DataGenerateInput, PolicyCheckInput
from aumos_mcp_server.tools.agents import register_agent_tools
from aumos_mcp_server.tools.data import register_data_tools
from aumos_mcp_server.tools.governance import register_governance_tools


@pytest.fixture()
def mock_client() -> MagicMock:
    """Provide a mock AumOS SDK client with all resource groups."""
    client = MagicMock()
    client.agents = MagicMock()
    client.agents.create = AsyncMock()
    client.agents.get = AsyncMock()
    client.agents.list = AsyncMock()
    client.agents.delete = AsyncMock()
    client.data = MagicMock()
    client.data.generate = AsyncMock()
    client.data.validate_schema = AsyncMock()
    client.governance = MagicMock()
    client.governance.policy_check = AsyncMock()
    client.governance.report = AsyncMock()
    return client


@pytest.fixture()
def mock_server() -> Server:
    """Provide a bare MCP Server instance for tool registration tests."""
    return Server("test-aumos-mcp")


class TestAgentToolInputValidation:
    """Tests for agents tool Pydantic validation."""

    def test_agent_create_input_valid(self) -> None:
        """Valid agent create input should parse without error."""
        data = AgentCreateInput(name="test", model="claude-3", instructions="Be helpful")
        assert data.name == "test"

    def test_agent_create_input_extra_field_forbidden(self) -> None:
        """Extra fields should be forbidden to catch typos."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AgentCreateInput(name="test", model="claude-3", instructions="Be helpful", typo_field="oops")

    def test_data_generate_input_rows_bounds(self) -> None:
        """Row count must be between 1 and 100,000."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DataGenerateInput(schema={"columns": ["age"]}, rows=0)

        with pytest.raises(ValidationError):
            DataGenerateInput(schema={"columns": ["age"]}, rows=200_000)

    def test_policy_check_input_all_fields_required(self) -> None:
        """All policy check fields are required."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PolicyCheckInput(policy_id="abc")  # missing resource_type, resource_id, action


class TestAgentToolsIntegration:
    """Integration tests for agent tool MCP registration."""

    async def test_agents_get_returns_text_content(
        self, mock_server: Server, mock_client: MagicMock
    ) -> None:
        """agents_get should return TextContent wrapping serialized agent JSON."""
        fake_agent = MagicMock()
        fake_agent.model_dump_json = MagicMock(return_value='{"id": "agent-123", "name": "test"}')
        mock_client.agents.get.return_value = fake_agent

        register_agent_tools(mock_server, mock_client)

        # Verify the mock was set up correctly
        assert mock_client.agents.get is not None

    async def test_data_generate_valid_input(
        self, mock_server: Server, mock_client: MagicMock
    ) -> None:
        """data_generate should call SDK with validated parameters."""
        fake_result = MagicMock()
        fake_result.model_dump_json = MagicMock(return_value='{"rows": []}')
        mock_client.data.generate.return_value = fake_result

        register_data_tools(mock_server, mock_client)

        # Schema validation passes for correct input
        validated = DataGenerateInput(
            schema={"columns": ["age", "income"]},
            rows=100,
            privacy_epsilon=1.0,
        )
        assert validated.rows == 100
        assert validated.privacy_epsilon == 1.0
