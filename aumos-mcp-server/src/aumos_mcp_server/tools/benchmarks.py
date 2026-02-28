"""MCP tool definitions for the AumOS Benchmark resource.

Registers: benchmarks_run, benchmarks_get_results.
"""

from __future__ import annotations

from mcp.server import Server
from mcp.types import TextContent

from aumos_mcp_server.schemas import BenchmarkGetResultsInput, BenchmarkRunInput


def register_benchmark_tools(server: Server, client: object) -> None:
    """Register AumOS benchmark MCP tools on the given server.

    Args:
        server: The MCP server instance to register tools on.
        client: The authenticated AumOS SDK client.
    """

    @server.tool()
    async def benchmarks_run(
        config_name: str,
        dataset_name: str = "",
    ) -> TextContent:
        """Submit a benchmark run against the AumOS platform.

        Args:
            config_name: Benchmark configuration name from the benchmark registry.
            dataset_name: Reference dataset to use (empty for default dataset).
        """
        validated = BenchmarkRunInput(
            config_name=config_name,
            dataset_name=dataset_name if dataset_name else None,
        )
        run = await client.benchmarks.run(  # type: ignore[attr-defined]
            config_name=validated.config_name,
            dataset_name=validated.dataset_name,
        )
        return TextContent(type="text", text=run.model_dump_json(indent=2))

    @server.tool()
    async def benchmarks_get_results(run_id: str) -> TextContent:
        """Retrieve the results of a completed benchmark run.

        Args:
            run_id: UUID of the benchmark run.
        """
        BenchmarkGetResultsInput(run_id=run_id)
        results = await client.benchmarks.get_results(run_id=run_id)  # type: ignore[attr-defined]
        return TextContent(type="text", text=results.model_dump_json(indent=2))
