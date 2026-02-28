"""MCP tool definitions for the AumOS Data Generation resource.

Registers: data_generate, data_preview, data_validate.
"""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.types import TextContent

from aumos_mcp_server.schemas import DataGenerateInput, DataPreviewInput


def register_data_tools(server: Server, client: object) -> None:
    """Register AumOS synthetic data generation MCP tools on the given server.

    Args:
        server: The MCP server instance to register tools on.
        client: The authenticated AumOS SDK client.
    """

    @server.tool()
    async def data_generate(
        schema: dict[str, Any],
        rows: int,
        privacy_epsilon: float = 1.0,
        modality: str = "tabular",
    ) -> TextContent:
        """Generate synthetic data matching the provided schema.

        Args:
            schema: Schema definition with column names and types (e.g., {'columns': ['age', 'income']}).
            rows: Number of synthetic rows to generate (1-100000).
            privacy_epsilon: Differential privacy epsilon (higher = less private, more accurate).
            modality: Data modality — 'tabular', 'text', or 'image'.
        """
        validated = DataGenerateInput(
            schema=schema,
            rows=rows,
            privacy_epsilon=privacy_epsilon,
            modality=modality,
        )
        result = await client.data.generate(  # type: ignore[attr-defined]
            schema=validated.schema,
            rows=validated.rows,
            privacy_epsilon=validated.privacy_epsilon,
            modality=validated.modality,
        )
        return TextContent(type="text", text=result.model_dump_json(indent=2))

    @server.tool()
    async def data_preview(
        schema: dict[str, Any],
        preview_rows: int = 5,
    ) -> TextContent:
        """Generate a small preview of synthetic data for schema inspection.

        Args:
            schema: Schema definition with column names and types.
            preview_rows: Number of preview rows (1-20).
        """
        validated = DataPreviewInput(schema=schema, preview_rows=preview_rows)
        result = await client.data.generate(  # type: ignore[attr-defined]
            schema=validated.schema,
            rows=validated.preview_rows,
            privacy_epsilon=10.0,  # high epsilon = fast preview with minimal privacy overhead
        )
        return TextContent(type="text", text=result.model_dump_json(indent=2))

    @server.tool()
    async def data_validate(schema: dict[str, Any]) -> TextContent:
        """Validate a data schema against AumOS schema requirements.

        Args:
            schema: Schema definition to validate.
        """
        result = await client.data.validate_schema(schema=schema)  # type: ignore[attr-defined]
        return TextContent(type="text", text=result.model_dump_json(indent=2))
