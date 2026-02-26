# AumOS Enterprise SDK

Official multi-language SDKs for the [AumOS Enterprise](https://aumos.io) platform.
Build AI-powered applications with production-grade agents, model management, governance, and observability.

## Available SDKs

| Language | Package | Docs |
|----------|---------|------|
| Python 3.11+ | `pip install aumos-sdk` | [python/README.md](python/README.md) |
| TypeScript / Node.js 18+ | `npm install @aumos/sdk` | [typescript/README.md](typescript/README.md) |
| Go 1.22+ | `go get go.aumos.io/sdk` | [go/README.md](go/README.md) |
| Java 17+ | Maven / Gradle | [java/README.md](java/README.md) |

## What Can You Build?

- **AI agent orchestration** — create, configure, and execute agents with custom tools
- **Model management** — query the registry of available models across providers
- **Governance** — enforce content policies, audit all platform actions
- **Observability** — monitor run status, token usage, and latency

## Quick Links

- **OpenAPI spec**: [openapi/aumos-api.yaml](openapi/aumos-api.yaml)
- **Code generation**: [openapi/codegen-config.yaml](openapi/codegen-config.yaml)
- **Examples**: [examples/](examples/)

## Getting Started

### Python

```python
import asyncio
from aumos_sdk import AumOSClient

async def main():
    async with AumOSClient() as client:  # reads AUMOS_API_KEY
        agent = await client.agents.create(
            name="my-first-agent",
            model_id="aumos:claude-opus-4-6",
            system_prompt="You are a helpful assistant.",
        )
        run = await client.agents.create_run(
            agent_id=agent.id,
            input={"message": "Hello, AumOS!"},
        )
        completed = await client.agents.wait_for_run(agent.id, run.id)
        print(completed.output)

asyncio.run(main())
```

### TypeScript

```typescript
import { AumOSClient } from "@aumos/sdk";

const client = new AumOSClient(); // reads AUMOS_API_KEY

const agent = await client.agents.create({
  name: "my-first-agent",
  modelId: "aumos:claude-opus-4-6",
});

const run = await client.agents.createRun(agent.id, {
  input: { message: "Hello, AumOS!" },
});

const completed = await client.agents.waitForRun(agent.id, run.id);
console.log(completed.output);
```

### Go

```go
client, _ := aumos.NewClient()

agent, _ := client.Agents.Create(ctx, aumos.CreateAgentRequest{
    Name:    "my-first-agent",
    ModelID: "aumos:claude-opus-4-6",
})

run, _ := client.Agents.CreateRun(ctx, agent.ID, aumos.CreateRunRequest{
    Input: map[string]interface{}{"message": "Hello, AumOS!"},
})

completed, _ := client.Agents.WaitForRun(ctx, agent.ID, run.ID, 2*time.Second, 5*time.Minute)
fmt.Println(completed.Output)
```

## Code Generation

SDKs can be regenerated from the master OpenAPI spec:

```bash
# Install openapi-generator
npm install -g @openapitools/openapi-generator-cli

# Regenerate all SDKs
make generate

# Regenerate a specific language
make generate-python
make generate-typescript
make generate-go
make generate-java
```

## Development

```bash
# Run all tests
make test

# Lint all SDKs
make lint

# Check a specific language
make test-python
make test-typescript
make test-go
make test-java
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
