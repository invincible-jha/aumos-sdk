"""MCP tool definitions for the AumOS Agents resource.

Registers: agents_create, agents_get, agents_list, agents_delete.
"""

from __future__ import annotations

import json

from mcp.server import Server
from mcp.types import TextContent

from aumos_mcp_server.schemas import AgentCreateInput, AgentGetInput, AgentListInput


def register_agent_tools(server: Server, client: object) -> None:
    """Register AumOS agent lifecycle MCP tools on the given server.

    Args:
        server: The MCP server instance to register tools on.
        client: The authenticated AumOS SDK client.
    """

    @server.tool()
    async def agents_create(name: str, model: str, instructions: str) -> TextContent:
        """Create a new AumOS agent with the specified configuration.

        Args:
            name: Human-readable name for the agent.
            model: Model identifier from the AumOS model registry.
            instructions: System prompt instructions for the agent.
        """
        validated = AgentCreateInput(name=name, model=model, instructions=instructions)
        agent = await client.agents.create(  # type: ignore[attr-defined]
            name=validated.name,
            model=validated.model,
            instructions=validated.instructions,
        )
        return TextContent(type="text", text=agent.model_dump_json(indent=2))

    @server.tool()
    async def agents_get(agent_id: str) -> TextContent:
        """Retrieve an AumOS agent by its unique identifier.

        Args:
            agent_id: UUID of the agent to retrieve.
        """
        AgentGetInput(agent_id=agent_id)
        agent = await client.agents.get(agent_id=agent_id)  # type: ignore[attr-defined]
        return TextContent(type="text", text=agent.model_dump_json(indent=2))

    @server.tool()
    async def agents_list(page_size: int = 20, page_token: str = "") -> TextContent:
        """List all AumOS agents in the current tenant.

        Args:
            page_size: Number of results per page (1-100).
            page_token: Pagination token for the next page.
        """
        token = page_token if page_token else None
        AgentListInput(page_size=page_size, page_token=token)
        page = await client.agents.list(page_size=page_size, page_token=token)  # type: ignore[attr-defined]
        return TextContent(type="text", text=page.model_dump_json(indent=2))

    @server.tool()
    async def agents_delete(agent_id: str) -> TextContent:
        """Delete an AumOS agent by its unique identifier.

        Args:
            agent_id: UUID of the agent to delete.
        """
        await client.agents.delete(agent_id=agent_id)  # type: ignore[attr-defined]
        return TextContent(type="text", text=json.dumps({"deleted": True, "agent_id": agent_id}))
