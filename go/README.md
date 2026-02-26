# AumOS Go SDK

Official Go SDK for the [AumOS Enterprise](https://aumos.io) platform.

## Requirements

- Go 1.22+
- AumOS API key

## Installation

```bash
go get go.aumos.io/sdk
```

## Quick Start

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"

    aumos "go.aumos.io/sdk"
)

func main() {
    client, err := aumos.NewClient()
    if err != nil {
        log.Fatal(err)
    }

    ctx := context.Background()

    // Create an agent
    agent, err := client.Agents.Create(ctx, aumos.CreateAgentRequest{
        Name:         "support-bot",
        ModelID:      "aumos:claude-opus-4-6",
        SystemPrompt: "You are a helpful enterprise support assistant.",
    })
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Created agent: %s\n", agent.ID)

    // Start a run
    run, err := client.Agents.CreateRun(ctx, agent.ID, aumos.CreateRunRequest{
        Input: map[string]interface{}{
            "message": "How do I reset my password?",
        },
    })
    if err != nil {
        log.Fatal(err)
    }

    // Wait for completion
    completed, err := client.Agents.WaitForRun(ctx, agent.ID, run.ID, 2*time.Second, 5*time.Minute)
    if err != nil {
        log.Fatal(err)
    }

    if completed.Succeeded() {
        fmt.Printf("Output: %v\n", completed.Output)
    } else {
        fmt.Printf("Run failed: %s\n", completed.Error)
    }
}
```

## Configuration

```go
client, err := aumos.NewClient(
    aumos.WithAPIKey("sk-aumos-..."),
    aumos.WithBaseURL("https://api.staging.aumos.io/v1"),
    aumos.WithTimeout(60 * time.Second),
    aumos.WithMaxRetries(5),
)
```

Or set the `AUMOS_API_KEY` environment variable and call `NewClient()` with no options.

## Agents

```go
// List agents
resp, err := client.Agents.List(ctx, aumos.ListAgentsOptions{
    Status:   aumos.AgentStatusActive,
    PageSize: 50,
})
for _, agent := range resp.Items {
    fmt.Println(agent.Name, agent.Status)
}

// Update an agent
inactive := aumos.AgentStatusInactive
updated, err := client.Agents.Update(ctx, agentID, aumos.UpdateAgentRequest{
    Status: &inactive,
})

// Delete
err = client.Agents.Delete(ctx, agentID)
```

## Error Handling

```go
import "errors"

agent, err := client.Agents.Get(ctx, agentID)
if err != nil {
    var apiErr *aumos.APIError
    if errors.As(err, &apiErr) {
        switch apiErr.StatusCode {
        case 404:
            fmt.Println("Agent not found")
        case 429:
            fmt.Println("Rate limited")
        default:
            fmt.Printf("API error %d: %s (requestId=%s)\n",
                apiErr.StatusCode, apiErr.Message, apiErr.RequestID)
        }
    }
    return err
}
```

## License

Apache 2.0 — see [LICENSE](../LICENSE) for details.
