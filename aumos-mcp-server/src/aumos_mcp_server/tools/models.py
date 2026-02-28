"""MCP tool definitions for the AumOS Model Registry resource.

Registers: models_register, models_get, models_list.
"""

from __future__ import annotations

from mcp.server import Server
from mcp.types import TextContent

from aumos_mcp_server.schemas import ModelGetInput, ModelRegisterInput


def register_model_tools(server: Server, client: object) -> None:
    """Register AumOS model registry MCP tools on the given server.

    Args:
        server: The MCP server instance to register tools on.
        client: The authenticated AumOS SDK client.
    """

    @server.tool()
    async def models_register(
        name: str,
        provider: str,
        model_id: str,
        capabilities: list[str] | None = None,
    ) -> TextContent:
        """Register a new model in the AumOS model registry.

        Args:
            name: Model display name.
            provider: Model provider (e.g., 'anthropic', 'openai', 'aumos').
            model_id: Provider-specific model identifier.
            capabilities: Optional capability tags (e.g., ['chat', 'function_calling']).
        """
        validated = ModelRegisterInput(
            name=name,
            provider=provider,
            model_id=model_id,
            capabilities=capabilities or [],
        )
        model = await client.models.register(  # type: ignore[attr-defined]
            name=validated.name,
            provider=validated.provider,
            model_id=validated.model_id,
            capabilities=validated.capabilities,
        )
        return TextContent(type="text", text=model.model_dump_json(indent=2))

    @server.tool()
    async def models_get(model_id: str) -> TextContent:
        """Retrieve a registered model by its AumOS registry UUID.

        Args:
            model_id: AumOS model registry UUID.
        """
        ModelGetInput(model_id=model_id)
        model = await client.models.get(model_id=model_id)  # type: ignore[attr-defined]
        return TextContent(type="text", text=model.model_dump_json(indent=2))

    @server.tool()
    async def models_list(page_size: int = 20) -> TextContent:
        """List all models registered in the AumOS model registry.

        Args:
            page_size: Number of results per page (1-100).
        """
        page = await client.models.list(page_size=page_size)  # type: ignore[attr-defined]
        return TextContent(type="text", text=page.model_dump_json(indent=2))
