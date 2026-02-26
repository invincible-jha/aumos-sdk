#!/usr/bin/env python3
# Copyright 2026 AumOS Enterprise
# Apache 2.0 License

"""AumOS Python SDK — Quickstart example.

Demonstrates the most common SDK patterns:
- Creating and managing agents
- Executing runs and waiting for results
- Listing models and governance audit logs
- Error handling

Run with:
    AUMOS_API_KEY=sk-aumos-... python quickstart.py
"""

from __future__ import annotations

import asyncio
import os

from aumos_sdk import (
    AumOSClient,
    AgentStatus,
    AgentTool,
    AumOSError,
    NotFoundError,
    RateLimitError,
    ToolType,
)


async def demonstrate_health_check(client: AumOSClient) -> None:
    """Show how to check platform health."""
    print("\n--- Health Check ---")
    health = await client.health()
    print(f"Status: {health.status} | Version: {health.version}")
    if not health.is_healthy:
        print("WARNING: Platform may be degraded. Proceeding anyway.")


async def demonstrate_agent_lifecycle(client: AumOSClient) -> str:
    """Create, inspect, and manage an agent. Returns the agent ID."""
    print("\n--- Agent Lifecycle ---")

    # Create an agent with a tool
    agent = await client.agents.create(
        name="quickstart-agent",
        model_id="aumos:claude-opus-4-6",
        description="Demo agent created by the Python SDK quickstart.",
        system_prompt=(
            "You are a helpful enterprise assistant. "
            "Answer questions clearly and concisely."
        ),
        tools=[
            AgentTool(
                name="search_knowledge_base",
                type=ToolType.RETRIEVAL,
                description="Search the internal knowledge base for answers.",
            )
        ],
        metadata={"created_by": "quickstart.py", "environment": "demo"},
    )
    print(f"Created agent: {agent.id} | Status: {agent.status.value}")

    # Retrieve it back
    fetched = await client.agents.get(agent.id)
    assert fetched.id == agent.id
    print(f"Fetched agent: {fetched.name}")

    # List agents — our new one should appear
    page = await client.agents.list(status=AgentStatus.ACTIVE, page_size=5)
    print(f"Active agents in tenant: {page.total}")

    return str(agent.id)


async def demonstrate_runs(client: AumOSClient, agent_id: str) -> None:
    """Create a run and wait for it to complete."""
    print("\n--- Run Execution ---")

    run = await client.agents.create_run(
        agent_id=agent_id,
        input={
            "message": "What is AumOS and how does it help enterprises?",
            "context": {"source": "quickstart-demo"},
        },
        timeout_seconds=120,
    )
    print(f"Run {run.id} started with status: {run.status.value}")

    # In a real scenario the run would be processed server-side.
    # Since this is a demo, we'll show how the polling API works.
    print("Polling for completion...")
    try:
        completed = await client.agents.wait_for_run(
            agent_id,
            run.id,
            poll_interval_seconds=2.0,
            max_wait_seconds=60.0,
        )
        if completed.succeeded:
            print(f"Run completed successfully!")
            if completed.output:
                print(f"Output: {completed.output}")
        else:
            print(f"Run ended with status: {completed.status.value}")
            if completed.error:
                print(f"Error: {completed.error}")
    except Exception as timeout_error:
        print(f"Polling timed out (expected in demo): {timeout_error}")

    # List runs for the agent
    runs_page = await client.agents.list_runs(agent_id, page_size=10)
    print(f"Total runs for agent: {runs_page.total}")


async def demonstrate_models(client: AumOSClient) -> None:
    """Show how to list and inspect models."""
    print("\n--- Models ---")

    models_page = await client.models.list(page_size=20)
    print(f"Available models: {len(models_page.items)}")
    for model in models_page.items[:3]:
        cap_str = ", ".join(model.capabilities)
        print(f"  {model.id}: {model.name} ({model.provider}) — {cap_str}")


async def demonstrate_governance(client: AumOSClient) -> None:
    """Show governance policy and audit log queries."""
    print("\n--- Governance ---")

    policies = await client.governance.list_policies()
    print(f"Governance policies: {len(policies.items)}")
    for policy in policies.items:
        status = "enabled" if policy.enabled else "disabled"
        print(f"  {policy.name} ({policy.type.value}) — {status}")

    logs = await client.governance.list_audit_logs(
        page_size=5,
        start_time="2026-01-01T00:00:00Z",
    )
    print(f"Recent audit log entries: {logs.total}")
    for entry in logs.items[:3]:
        print(f"  [{entry.timestamp}] {entry.action} by {entry.actor_id} — {entry.outcome}")


async def demonstrate_error_handling(client: AumOSClient) -> None:
    """Demonstrate structured error handling."""
    print("\n--- Error Handling ---")

    try:
        await client.agents.get("00000000-0000-0000-0000-000000000000")
    except NotFoundError as exc:
        print(f"Caught NotFoundError: {exc} (HTTP {exc.status_code})")
    except RateLimitError as exc:
        print(f"Rate limited — retry after {exc.retry_after}s")
    except AumOSError as exc:
        print(f"SDK error: {exc} (request_id={exc.request_id})")


async def cleanup(client: AumOSClient, agent_id: str) -> None:
    """Clean up demo resources."""
    print("\n--- Cleanup ---")
    await client.agents.delete(agent_id)
    print(f"Deleted agent {agent_id}")


async def main() -> None:
    api_key = os.environ.get("AUMOS_API_KEY")
    if not api_key:
        print("Set AUMOS_API_KEY to run this quickstart against the live API.")
        print("Continuing in demonstration mode (errors are expected).\n")

    async with AumOSClient(api_key=api_key or "sk-demo-key") as client:
        print("AumOS Python SDK Quickstart")
        print("=" * 40)

        await demonstrate_health_check(client)

        agent_id = await demonstrate_agent_lifecycle(client)
        await demonstrate_runs(client, agent_id)
        await demonstrate_models(client)
        await demonstrate_governance(client)
        await demonstrate_error_handling(client)
        await cleanup(client, agent_id)

        print("\nQuickstart complete.")


if __name__ == "__main__":
    asyncio.run(main())
