"""AumOS MCP server — entry point for stdio and HTTP/SSE transports.

Supported transports:
- stdio: for Claude Desktop and local CLI agents (aumos-mcp-server command)
- HTTP/SSE: for remote agent integrations (requires 'http' optional dependency)

Claude Desktop configuration:
    {
      "mcpServers": {
        "aumos": {
          "command": "uvx",
          "args": ["aumos-mcp-server"],
          "env": {
            "AUMOS_API_KEY": "your-api-key",
            "AUMOS_BASE_URL": "https://api.aumos.ai"
          }
        }
      }
    }
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server

from aumos_mcp_server.config import MCPServerConfig
from aumos_mcp_server.tools.agents import register_agent_tools
from aumos_mcp_server.tools.benchmarks import register_benchmark_tools
from aumos_mcp_server.tools.data import register_data_tools
from aumos_mcp_server.tools.governance import register_governance_tools
from aumos_mcp_server.tools.models import register_model_tools
from aumos_mcp_server.tools.runs import register_run_tools


def create_server(config: MCPServerConfig) -> Server:
    """Create and configure the AumOS MCP server with all tool groups registered.

    Args:
        config: Server configuration including API credentials and base URL.

    Returns:
        Configured MCP server with all AumOS tools registered.
    """
    # Import here to avoid mandatory aumos_sdk dependency at module level
    try:
        from aumos_sdk import AumOSClient  # type: ignore[import]

        client: Any = AumOSClient(
            api_key=config.api_key,
            base_url=str(config.aumos_base_url),
            max_retries=config.max_retries,
        )
    except ImportError as exc:
        raise ImportError(
            "aumos-sdk is required. Install with: pip install aumos-sdk"
        ) from exc

    server = Server("aumos-mcp-server")

    register_agent_tools(server, client)
    register_run_tools(server, client)
    register_model_tools(server, client)
    register_governance_tools(server, client)
    register_data_tools(server, client)
    register_benchmark_tools(server, client)

    return server


async def run_stdio() -> None:
    """Entry point for stdio transport — used by Claude Desktop and local agents.

    Reads AUMOS_API_KEY and AUMOS_BASE_URL from environment variables.
    Will raise ValidationError with a clear message if AUMOS_API_KEY is missing.
    """
    config = MCPServerConfig()
    server = create_server(config)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Synchronous entry point for the aumos-mcp-server console script."""
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
