# @aumos/sdk — TypeScript SDK

Official TypeScript/JavaScript SDK for the [AumOS Enterprise](https://aumos.io) platform.
Works in Node.js 18+ and modern browser environments via the native Fetch API.

## Installation

```bash
npm install @aumos/sdk
# or
yarn add @aumos/sdk
# or
pnpm add @aumos/sdk
```

## Quick Start

```typescript
import { AumOSClient } from "@aumos/sdk";

const client = new AumOSClient({ apiKey: process.env.AUMOS_API_KEY });

// Create an agent
const agent = await client.agents.create({
  name: "support-bot",
  modelId: "aumos:claude-opus-4-6",
  systemPrompt: "You are a helpful enterprise support assistant.",
});

// Execute a run
const run = await client.agents.createRun(agent.id, {
  input: { message: "How do I reset my password?" },
});

// Wait for completion
const completed = await client.agents.waitForRun(agent.id, run.id);
if (completed.status === "completed") {
  console.log("Response:", completed.output);
}
```

## Authentication

```typescript
// Explicit API key
const client = new AumOSClient({ apiKey: "sk-aumos-..." });

// From environment variable AUMOS_API_KEY (Node.js only)
const client = new AumOSClient();
```

## Agents

```typescript
import { AumOSClient, AgentStatus } from "@aumos/sdk";

const client = new AumOSClient();

// List agents
const { items, total } = await client.agents.list({ pageSize: 50 });

// Create with tools
const agent = await client.agents.create({
  name: "analyst",
  modelId: "aumos:claude-opus-4-6",
  tools: [
    {
      name: "execute_query",
      type: "function",
      description: "Execute a SQL query",
      parameters: {
        type: "object",
        properties: { query: { type: "string" } },
        required: ["query"],
      },
    },
  ],
});

// Update
const updated = await client.agents.update(agent.id, {
  status: "inactive",
});

// Delete
await client.agents.delete(agent.id);
```

## Runs

```typescript
// Start and poll manually
let run = await client.agents.createRun(agentId, {
  input: { task: "summarize Q4 report" },
  timeoutSeconds: 600,
});

while (!["completed", "failed", "cancelled", "timeout"].includes(run.status)) {
  await new Promise((r) => setTimeout(r, 2000));
  run = await client.runs.get(run.id);
}

// Or use built-in polling
const completed = await client.agents.waitForRun(agentId, run.id, {
  pollIntervalMs: 3000,
  maxWaitMs: 600_000,
});
```

## Error Handling

```typescript
import {
  AumOSClient,
  AumOSError,
  AumOSNotFoundError,
  AumOSRateLimitError,
  AumOSAuthenticationError,
} from "@aumos/sdk";

try {
  const agent = await client.agents.get(agentId);
} catch (error) {
  if (error instanceof AumOSNotFoundError) {
    console.log("Agent not found");
  } else if (error instanceof AumOSRateLimitError) {
    console.log(`Rate limited. Retry after ${error.retryAfterMs}ms`);
  } else if (error instanceof AumOSAuthenticationError) {
    console.log("Check your API key");
  } else if (error instanceof AumOSError) {
    console.log(`SDK error: ${error.message} (requestId=${error.requestId})`);
  }
}
```

## License

Apache 2.0 — see [LICENSE](../LICENSE) for details.
