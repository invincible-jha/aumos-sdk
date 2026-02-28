"""MCP tool definitions for the AumOS Governance resource.

Registers: governance_policy_check, governance_report.
"""

from __future__ import annotations

from mcp.server import Server
from mcp.types import TextContent

from aumos_mcp_server.schemas import GovernanceReportInput, PolicyCheckInput


def register_governance_tools(server: Server, client: object) -> None:
    """Register AumOS governance MCP tools on the given server.

    Args:
        server: The MCP server instance to register tools on.
        client: The authenticated AumOS SDK client.
    """

    @server.tool()
    async def governance_policy_check(
        policy_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
    ) -> TextContent:
        """Evaluate whether a proposed action passes AumOS governance policies.

        Args:
            policy_id: UUID of the policy to evaluate.
            resource_type: Type of resource being checked (e.g., 'dataset', 'agent').
            resource_id: UUID of the resource to check.
            action: Proposed action (e.g., 'generate', 'export', 'delete').
        """
        validated = PolicyCheckInput(
            policy_id=policy_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
        )
        result = await client.governance.policy_check(  # type: ignore[attr-defined]
            policy_id=validated.policy_id,
            resource_type=validated.resource_type,
            resource_id=validated.resource_id,
            action=validated.action,
        )
        return TextContent(type="text", text=result.model_dump_json(indent=2))

    @server.tool()
    async def governance_report(
        start_date: str,
        end_date: str,
        policy_ids: list[str] | None = None,
    ) -> TextContent:
        """Generate a governance audit report for the specified date range.

        Args:
            start_date: ISO 8601 start date (e.g., '2025-01-01').
            end_date: ISO 8601 end date (e.g., '2025-12-31').
            policy_ids: Optional list of policy UUIDs to filter by.
        """
        validated = GovernanceReportInput(
            start_date=start_date,
            end_date=end_date,
            policy_ids=policy_ids,
        )
        report = await client.governance.report(  # type: ignore[attr-defined]
            start_date=validated.start_date,
            end_date=validated.end_date,
            policy_ids=validated.policy_ids,
        )
        return TextContent(type="text", text=report.model_dump_json(indent=2))
