# AumOS Python SDK

Official Python SDK for the [AumOS Enterprise](https://aumos.io) platform.
Provides async-first access to agents, model registry, governance, and observability APIs.

## Requirements

- Python 3.11 or 3.12
- An AumOS account and API key

## Installation

```bash
pip install aumos-sdk
```

## Quick Start

```python
import asyncio
from aumos_sdk import AumOSClient

async def main():
    async with AumOSClient(api_key="sk-aumos-...") as client:
        # Check platform health
        health = await client.health()
        print(f"Platform status: {health.status}")

        # Create an agent
        agent = await client.agents.create(
            name="support-bot",
            model_id="aumos:claude-opus-4-6",
            system_prompt="You are a helpful enterprise support assistant.",
        )
        print(f"Created agent: {agent.id}")

        # Execute a run
        run = await client.agents.create_run(
            agent_id=agent.id,
            input={"message": "How do I reset my password?"},
        )

        # Wait for completion
        completed = await client.agents.wait_for_run(agent.id, run.id)
        if completed.succeeded:
            print(f"Response: {completed.output}")
        else:
            print(f"Run failed: {completed.error}")

asyncio.run(main())
```

## Authentication

### API Key (recommended)

```python
# Explicit
client = AumOSClient(api_key="sk-aumos-...")

# From environment variable AUMOS_API_KEY
client = AumOSClient()
```

### Bearer Token

```python
import time
from aumos_sdk import AumOSClient

client = AumOSClient(
    token="eyJ...",
    expires_at=time.time() + 3600,
)
```

## Agents

```python
# List agents
response = await client.agents.list(page_size=50)
for agent in response.items:
    print(agent.name, agent.status)

# Create an agent with tools
from aumos_sdk import AgentTool, ToolType

agent = await client.agents.create(
    name="data-analyst",
    model_id="aumos:claude-opus-4-6",
    system_prompt="Analyze data and produce structured reports.",
    tools=[
        AgentTool(
            name="execute_query",
            type=ToolType.FUNCTION,
            description="Execute a SQL query against the data warehouse",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            },
        )
    ],
)

# Update an agent
from aumos_sdk import AgentStatus
updated = await client.agents.update(
    agent.id,
    status=AgentStatus.INACTIVE,
)

# Delete an agent
await client.agents.delete(agent.id)
```

## Runs

```python
# Start a run and poll manually
run = await client.agents.create_run(
    agent_id=agent_id,
    input={"task": "summarize Q4 earnings"},
    timeout_seconds=600,
)

# Poll via the runs resource
import asyncio
while not run.is_terminal:
    await asyncio.sleep(2)
    run = await client.runs.get(run.id)

# Or use built-in polling
completed = await client.agents.wait_for_run(
    agent_id,
    run.id,
    poll_interval_seconds=3.0,
    max_wait_seconds=600.0,
)
```

## Models

```python
# List available models
models = await client.models.list(provider="anthropic")
for model in models.items:
    print(f"{model.id}: {model.name} ({model.context_window} tokens)")

# Get a specific model
model = await client.models.get("aumos:claude-opus-4-6")
print(model.capabilities)
```

## Governance

```python
# List policies
policies = await client.governance.list_policies()

# Query audit logs
from datetime import datetime, UTC
logs = await client.governance.list_audit_logs(
    start_time="2026-01-01T00:00:00Z",
    end_time="2026-02-01T00:00:00Z",
    action="agent.run.create",
)
for entry in logs.items:
    print(f"{entry.timestamp} | {entry.action} | {entry.outcome}")
```

## Error Handling

```python
from aumos_sdk import (
    AumOSClient,
    AumOSError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
import asyncio

async def safe_get_agent(client: AumOSClient, agent_id: str):
    try:
        return await client.agents.get(agent_id)
    except NotFoundError:
        print(f"Agent {agent_id} does not exist.")
        return None
    except AuthenticationError:
        print("Check your API key.")
        raise
    except RateLimitError as exc:
        print(f"Rate limited. Retry after {exc.retry_after}s")
        raise
    except AumOSError as exc:
        print(f"SDK error: {exc} (request_id={exc.request_id})")
        raise
```

## Configuration

| Parameter | Environment Variable | Default |
|-----------|---------------------|---------|
| `api_key` | `AUMOS_API_KEY` | — |
| `base_url` | — | `https://api.aumos.io/v1` |
| `timeout` | — | `30.0` |
| `max_retries` | — | `3` |

## License

Apache 2.0 — see [LICENSE](../LICENSE) for details.
