# AumOS Java SDK

Official Java SDK for the [AumOS Enterprise](https://aumos.io) platform.
Requires Java 17+.

## Installation

### Maven

```xml
<dependency>
    <groupId>io.aumos</groupId>
    <artifactId>aumos-sdk</artifactId>
    <version>1.0.0</version>
</dependency>
```

### Gradle

```groovy
implementation 'io.aumos:aumos-sdk:1.0.0'
```

## Quick Start

```java
import io.aumos.sdk.AumOSClient;
import java.util.Map;

public class QuickStart {
    public static void main(String[] args) throws InterruptedException {
        try (AumOSClient client = AumOSClient.builder()
                .apiKey(System.getenv("AUMOS_API_KEY"))
                .build()) {

            // Create an agent
            Map<String, Object> agent = client.agents().create(Map.of(
                "name", "support-bot",
                "modelId", "aumos:claude-opus-4-6",
                "systemPrompt", "You are a helpful assistant."
            ));
            String agentId = (String) agent.get("id");

            // Start a run
            Map<String, Object> run = client.agents().createRun(agentId, Map.of(
                "input", Map.of("message", "Hello!")
            ));
            String runId = (String) run.get("id");

            // Wait for completion (2s poll, 5min max)
            Map<String, Object> completed = client.agents().waitForRun(
                agentId, runId, 2_000L, 300_000L
            );

            System.out.println("Status: " + completed.get("status"));
            System.out.println("Output: " + completed.get("output"));
        }
    }
}
```

## Error Handling

```java
import io.aumos.sdk.AumOSClient;

try {
    Map<String, Object> agent = client.agents().get(agentId);
} catch (AumOSClient.AumOSAPIException e) {
    if (e.getStatusCode() == 404) {
        System.out.println("Agent not found");
    } else if (e.getStatusCode() == 429) {
        System.out.println("Rate limited (requestId=" + e.getRequestId() + ")");
    }
} catch (AumOSClient.AumOSNetworkException e) {
    System.out.println("Network error: " + e.getMessage());
}
```

## License

Apache 2.0 — see [LICENSE](../LICENSE) for details.
