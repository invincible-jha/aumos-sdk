// Copyright 2026 AumOS Enterprise
// Apache 2.0 License

/**
 * AumOS TypeScript SDK — Quickstart example.
 *
 * Demonstrates the most common SDK patterns:
 * - Creating and managing agents
 * - Executing runs and waiting for results
 * - Listing models and governance audit logs
 * - Structured error handling
 *
 * Run with:
 *   AUMOS_API_KEY=sk-aumos-... npx tsx quickstart.ts
 */

import {
  AumOSClient,
  AumOSError,
  AumOSNotFoundError,
  AumOSRateLimitError,
  type Agent,
} from "@aumos/sdk";

const client = new AumOSClient({
  apiKey: process.env["AUMOS_API_KEY"] ?? "sk-demo-key",
});

async function demonstrateHealthCheck(): Promise<void> {
  console.log("\n--- Health Check ---");
  const health = await client.health();
  console.log(`Status: ${health.status} | Version: ${health.version}`);
}

async function demonstrateAgentLifecycle(): Promise<string> {
  console.log("\n--- Agent Lifecycle ---");

  const agent = await client.agents.create({
    name: "quickstart-agent",
    modelId: "aumos:claude-opus-4-6",
    description: "Demo agent created by the TypeScript SDK quickstart.",
    systemPrompt:
      "You are a helpful enterprise assistant. Answer questions clearly.",
    tools: [
      {
        name: "search_knowledge_base",
        type: "retrieval",
        description: "Search the internal knowledge base.",
      },
    ],
    metadata: { createdBy: "quickstart.ts", environment: "demo" },
  });

  console.log(`Created agent: ${agent.id} | Status: ${agent.status}`);

  // Retrieve and verify
  const fetched = await client.agents.get(agent.id);
  console.log(`Fetched agent: ${fetched.name}`);

  // List active agents
  const { items, total } = await client.agents.list({
    status: "active",
    pageSize: 5,
  });
  console.log(`Active agents in tenant: ${total}`);

  return agent.id;
}

async function demonstrateRuns(agentId: string): Promise<void> {
  console.log("\n--- Run Execution ---");

  const run = await client.agents.createRun(agentId, {
    input: {
      message: "What is AumOS and how does it help enterprises?",
      context: { source: "quickstart-demo" },
    },
    timeoutSeconds: 120,
  });
  console.log(`Run ${run.id} started with status: ${run.status}`);

  console.log("Polling for completion...");
  try {
    const completed = await client.agents.waitForRun(agentId, run.id, {
      pollIntervalMs: 2_000,
      maxWaitMs: 60_000,
    });

    if (completed.status === "completed") {
      console.log("Run completed successfully!");
      if (completed.output) {
        console.log("Output:", JSON.stringify(completed.output, null, 2));
      }
    } else {
      console.log(`Run ended with status: ${completed.status}`);
      if (completed.error) {
        console.log(`Error: ${completed.error}`);
      }
    }
  } catch (error) {
    console.log(`Polling timed out (expected in demo): ${error}`);
  }

  // List runs
  const runsPage = await client.agents.listRuns(agentId, { pageSize: 10 });
  console.log(`Total runs for agent: ${runsPage.total}`);
}

async function demonstrateModels(): Promise<void> {
  console.log("\n--- Models ---");

  const modelsPage = await client.models.list({ pageSize: 20 });
  console.log(`Available models: ${modelsPage.items.length}`);

  for (const model of modelsPage.items.slice(0, 3)) {
    const caps = model.capabilities.join(", ");
    console.log(`  ${model.id}: ${model.name} (${model.provider}) — ${caps}`);
  }
}

async function demonstrateGovernance(): Promise<void> {
  console.log("\n--- Governance ---");

  const policies = await client.governance.listPolicies();
  console.log(`Governance policies: ${policies.items.length}`);
  for (const policy of policies.items) {
    const status = policy.enabled ? "enabled" : "disabled";
    console.log(`  ${policy.name} (${policy.type}) — ${status}`);
  }

  const logs = await client.governance.listAuditLogs({
    pageSize: 5,
    startTime: "2026-01-01T00:00:00Z",
  });
  console.log(`Recent audit log entries: ${logs.total}`);
  for (const entry of logs.items.slice(0, 3)) {
    console.log(`  [${entry.timestamp}] ${entry.action} by ${entry.actorId} — ${entry.outcome}`);
  }
}

async function demonstrateErrorHandling(): Promise<void> {
  console.log("\n--- Error Handling ---");

  try {
    await client.agents.get("00000000-0000-0000-0000-000000000000");
  } catch (error) {
    if (error instanceof AumOSNotFoundError) {
      console.log(`Caught AumOSNotFoundError: ${error.message} (HTTP ${error.statusCode})`);
    } else if (error instanceof AumOSRateLimitError) {
      console.log(`Rate limited — retry after ${error.retryAfterMs}ms`);
    } else if (error instanceof AumOSError) {
      console.log(`SDK error: ${error.message} (requestId=${error.requestId})`);
    }
  }
}

async function cleanup(agentId: string): Promise<void> {
  console.log("\n--- Cleanup ---");
  await client.agents.delete(agentId);
  console.log(`Deleted agent ${agentId}`);
}

async function main(): Promise<void> {
  if (!process.env["AUMOS_API_KEY"]) {
    console.log("Set AUMOS_API_KEY to run against the live API.");
    console.log("Continuing in demonstration mode (errors are expected).\n");
  }

  console.log("AumOS TypeScript SDK Quickstart");
  console.log("=".repeat(40));

  await demonstrateHealthCheck();

  const agentId = await demonstrateAgentLifecycle();
  await demonstrateRuns(agentId);
  await demonstrateModels();
  await demonstrateGovernance();
  await demonstrateErrorHandling();
  await cleanup(agentId);

  console.log("\nQuickstart complete.");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
