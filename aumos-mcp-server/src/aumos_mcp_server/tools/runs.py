"""MCP tool definitions for the AumOS Runs resource.

Registers: runs_create, runs_get, runs_cancel.
"""

from __future__ import annotations

import json

from mcp.server import Server
from mcp.types import TextContent

from aumos_mcp_server.schemas import RunCancelInput, RunCreateInput, RunGetInput


def register_run_tools(server: Server, client: object) -> None:
    """Register AumOS run lifecycle MCP tools on the given server.

    Args:
        server: The MCP server instance to register tools on.
        client: The authenticated AumOS SDK client.
    """

    @server.tool()
    async def runs_create(agent_id: str, input_text: str, thread_id: str = "") -> TextContent:
        """Create a new agent run and return when the run completes.

        Args:
            agent_id: UUID of the agent to run.
            input_text: User message to send to the agent.
            thread_id: Existing thread UUID (empty string to create a new thread).
        """
        validated = RunCreateInput(
            agent_id=agent_id,
            input_text=input_text,
            thread_id=thread_id if thread_id else None,
        )
        run = await client.runs.create(  # type: ignore[attr-defined]
            agent_id=validated.agent_id,
            thread_id=validated.thread_id,
            input_text=validated.input_text,
        )
        return TextContent(type="text", text=run.model_dump_json(indent=2))

    @server.tool()
    async def runs_get(run_id: str) -> TextContent:
        """Retrieve the status and output of a completed run.

        Args:
            run_id: UUID of the run to retrieve.
        """
        RunGetInput(run_id=run_id)
        run = await client.runs.get(run_id=run_id)  # type: ignore[attr-defined]
        return TextContent(type="text", text=run.model_dump_json(indent=2))

    @server.tool()
    async def runs_cancel(run_id: str) -> TextContent:
        """Cancel an in-progress agent run.

        Args:
            run_id: UUID of the run to cancel.
        """
        RunCancelInput(run_id=run_id)
        await client.runs.cancel(run_id=run_id)  # type: ignore[attr-defined]
        return TextContent(type="text", text=json.dumps({"cancelled": True, "run_id": run_id}))
