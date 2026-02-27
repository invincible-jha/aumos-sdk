"""Integration guide generator for the AumOS SDK.

Generates per-service integration guides, complete code examples for all SDK
languages, troubleshooting FAQs, migration guides between SDK versions, and
exports documentation as Markdown for inclusion in the SDK docs site.
"""

from datetime import datetime, timezone
from typing import Any

# Supported languages for code examples
_SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"python", "typescript", "go", "java"})

# Supported AumOS service areas
_SUPPORTED_SERVICES: frozenset[str] = frozenset({
    "agents",
    "runs",
    "models",
    "governance",
    "synthetic_data",
    "privacy",
    "authentication",
})

# Language display names for documentation
_LANGUAGE_DISPLAY: dict[str, str] = {
    "python": "Python",
    "typescript": "TypeScript",
    "go": "Go",
    "java": "Java",
}

# Per-service, per-language code examples
_CODE_EXAMPLES: dict[str, dict[str, str]] = {
    "agents": {
        "python": '''\
import asyncio
from aumos_sdk import AumOSClient

async def main():
    async with AumOSClient(api_key="your-api-key") as client:
        # Create an agent
        agent = await client.agents.create(
            name="my-enterprise-agent",
            model_id="aumos:claude-opus-4-6",
            system_prompt="You are a helpful enterprise assistant.",
        )
        print(f"Created agent: {agent.id}")

        # List agents
        agents_page = await client.agents.list(page_size=20)
        for a in agents_page.items:
            print(f"  - {a.name}: {a.id}")

asyncio.run(main())
''',
        "typescript": '''\
import { AumOSClient } from "@aumos/sdk";

const client = new AumOSClient({ apiKey: "your-api-key" });

// Create an agent
const agent = await client.agents.create({
  name: "my-enterprise-agent",
  modelId: "aumos:claude-opus-4-6",
  systemPrompt: "You are a helpful enterprise assistant.",
});
console.log("Created agent:", agent.id);

// List agents
const page = await client.agents.list({ pageSize: 20 });
for (const a of page.items) {
  console.log(`  - ${a.name}: ${a.id}`);
}
''',
        "go": '''\
package main

import (
    "context"
    "fmt"
    "log"

    aumos "github.com/aumos/aumos-sdk-go"
)

func main() {
    client := aumos.NewClient(aumos.WithAPIKey("your-api-key"))
    ctx := context.Background()

    // Create an agent
    agent, err := client.Agents.Create(ctx, aumos.CreateAgentRequest{
        Name:         "my-enterprise-agent",
        ModelID:      "aumos:claude-opus-4-6",
        SystemPrompt: "You are a helpful enterprise assistant.",
    })
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Created agent: %s\\n", agent.ID)

    // List agents
    page, err := client.Agents.List(ctx, aumos.ListAgentsRequest{PageSize: 20})
    if err != nil {
        log.Fatal(err)
    }
    for _, a := range page.Items {
        fmt.Printf("  - %s: %s\\n", a.Name, a.ID)
    }
}
''',
        "java": '''\
import io.aumos.sdk.AumOSClient;
import io.aumos.sdk.models.Agent;
import io.aumos.sdk.models.AgentPage;
import io.aumos.sdk.requests.CreateAgentRequest;

public class AgentsExample {
    public static void main(String[] args) throws Exception {
        try (AumOSClient client = AumOSClient.builder()
                .apiKey("your-api-key")
                .build()) {

            // Create an agent
            Agent agent = client.agents().create(
                CreateAgentRequest.builder()
                    .name("my-enterprise-agent")
                    .modelId("aumos:claude-opus-4-6")
                    .systemPrompt("You are a helpful enterprise assistant.")
                    .build()
            );
            System.out.println("Created agent: " + agent.getId());

            // List agents
            AgentPage page = client.agents().list(20, 1);
            for (Agent a : page.getItems()) {
                System.out.printf("  - %s: %s%n", a.getName(), a.getId());
            }
        }
    }
}
''',
    },
    "synthetic_data": {
        "python": '''\
import asyncio
from aumos_sdk import AumOSClient

async def main():
    async with AumOSClient(api_key="your-api-key") as client:
        # Start a tabular data generation job
        run = await client.runs.create_tabular(
            dataset_name="retail-q4-2025",
            row_count=10000,
            privacy_mode="differential_privacy",
            epsilon=1.0,
        )
        print(f"Generation job started: {run.id}, status: {run.status}")

        # Poll until complete
        while run.status in ("pending", "running"):
            await asyncio.sleep(5)
            run = await client.runs.get(run.id)
            print(f"  Status: {run.status}")

        if run.status == "completed":
            print(f"Dataset ready: {run.output_url}")
        else:
            print(f"Job failed: {run.error_message}")

asyncio.run(main())
''',
        "typescript": '''\
import { AumOSClient } from "@aumos/sdk";

const client = new AumOSClient({ apiKey: "your-api-key" });

// Start a tabular data generation job
let run = await client.runs.createTabular({
  datasetName: "retail-q4-2025",
  rowCount: 10000,
  privacyMode: "differential_privacy",
  epsilon: 1.0,
});
console.log(`Generation job started: ${run.id}, status: ${run.status}`);

// Poll until complete
while (run.status === "pending" || run.status === "running") {
  await new Promise((r) => setTimeout(r, 5000));
  run = await client.runs.get(run.id);
  console.log(`  Status: ${run.status}`);
}

if (run.status === "completed") {
  console.log("Dataset ready:", run.outputUrl);
} else {
  console.error("Job failed:", run.errorMessage);
}
''',
        "go": '''\
package main

import (
    "context"
    "fmt"
    "log"
    "time"

    aumos "github.com/aumos/aumos-sdk-go"
)

func main() {
    client := aumos.NewClient(aumos.WithAPIKey("your-api-key"))
    ctx := context.Background()

    run, err := client.Runs.CreateTabular(ctx, aumos.TabularGenerationRequest{
        DatasetName: "retail-q4-2025",
        RowCount:    10000,
        PrivacyMode: "differential_privacy",
        Epsilon:     1.0,
    })
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Job started: %s\\n", run.ID)

    for run.Status == "pending" || run.Status == "running" {
        time.Sleep(5 * time.Second)
        run, err = client.Runs.Get(ctx, run.ID)
        if err != nil {
            log.Fatal(err)
        }
        fmt.Printf("  Status: %s\\n", run.Status)
    }

    if run.Status == "completed" {
        fmt.Printf("Dataset ready: %s\\n", run.OutputURL)
    } else {
        fmt.Printf("Job failed: %s\\n", run.ErrorMessage)
    }
}
''',
        "java": '''\
import io.aumos.sdk.AumOSClient;
import io.aumos.sdk.models.Run;
import io.aumos.sdk.requests.TabularGenerationRequest;

public class SyntheticDataExample {
    public static void main(String[] args) throws Exception {
        try (AumOSClient client = AumOSClient.builder().apiKey("your-api-key").build()) {

            Run run = client.runs().createTabular(
                TabularGenerationRequest.builder()
                    .datasetName("retail-q4-2025")
                    .rowCount(10000)
                    .privacyMode("differential_privacy")
                    .epsilon(1.0)
                    .build()
            );
            System.out.println("Job started: " + run.getId());

            while ("pending".equals(run.getStatus()) || "running".equals(run.getStatus())) {
                Thread.sleep(5000);
                run = client.runs().get(run.getId());
                System.out.println("  Status: " + run.getStatus());
            }

            if ("completed".equals(run.getStatus())) {
                System.out.println("Dataset ready: " + run.getOutputUrl());
            } else {
                System.err.println("Job failed: " + run.getErrorMessage());
            }
        }
    }
}
''',
    },
    "authentication": {
        "python": '''\
from aumos_sdk import AumOSClient
from aumos_sdk.auth import ApiKeyAuth, BearerTokenAuth

# API key authentication (recommended for production)
client = AumOSClient(api_key="aumos-key-your-api-key")

# Bearer token authentication (for OAuth flows)
client = AumOSClient(auth=BearerTokenAuth(token="eyJ..."))

# Environment variable (API key auto-loaded from AUMOS_API_KEY)
import os
os.environ["AUMOS_API_KEY"] = "aumos-key-your-api-key"
client = AumOSClient()
''',
        "typescript": '''\
import { AumOSClient } from "@aumos/sdk";

// API key authentication
const client = new AumOSClient({ apiKey: "aumos-key-your-api-key" });

// Bearer token authentication
const clientWithToken = new AumOSClient({
  auth: { type: "bearer", token: "eyJ..." },
});

// Environment variable (auto-loaded from AUMOS_API_KEY)
const clientFromEnv = new AumOSClient(); // reads process.env.AUMOS_API_KEY
''',
        "go": '''\
import aumos "github.com/aumos/aumos-sdk-go"

// API key authentication
client := aumos.NewClient(aumos.WithAPIKey("aumos-key-your-api-key"))

// Bearer token authentication
clientWithToken := aumos.NewClient(aumos.WithBearerToken("eyJ..."))

// From environment variable (AUMOS_API_KEY)
clientFromEnv := aumos.NewClient(aumos.WithAPIKeyFromEnv())
''',
        "java": '''\
import io.aumos.sdk.AumOSClient;

// API key authentication
AumOSClient client = AumOSClient.builder()
    .apiKey("aumos-key-your-api-key")
    .build();

// Bearer token authentication
AumOSClient tokenClient = AumOSClient.builder()
    .bearerToken("eyJ...")
    .build();

// From environment variable (AUMOS_API_KEY)
AumOSClient envClient = AumOSClient.builder()
    .apiKeyFromEnv()
    .build();
''',
    },
}

# Troubleshooting FAQ entries
_TROUBLESHOOTING_FAQ: list[dict[str, str]] = [
    {
        "question": "I'm getting a 401 AuthenticationError. What's wrong?",
        "answer": (
            "Your API key is missing, malformed, or has been revoked. "
            "Verify the key is set correctly (e.g., AUMOS_API_KEY environment variable or "
            "passed directly to the AumOSClient constructor). API keys start with 'aumos-key-'. "
            "Generate a new key in the AumOS console at https://console.aumos.ai/settings/api-keys."
        ),
    },
    {
        "question": "My generation jobs are timing out. How do I fix this?",
        "answer": (
            "Large generation jobs (>100k rows) can take several minutes. "
            "Increase your client timeout (e.g., http_timeout=300 in Python) and "
            "poll the job status via GET /api/v1/runs/{run_id} rather than waiting synchronously. "
            "For very large jobs, use the streaming endpoint instead."
        ),
    },
    {
        "question": "How do I handle rate limiting (429 errors)?",
        "answer": (
            "The SDK automatically retries 429 responses with exponential backoff. "
            "Inspect the Retry-After header to determine the wait time. "
            "Reduce concurrency or contact support to increase your rate limit tier."
        ),
    },
    {
        "question": "Why is my fidelity score low on generated tabular data?",
        "answer": (
            "Low fidelity typically indicates insufficient training data, too-strict "
            "differential privacy (epsilon < 0.5), or a schema mismatch. "
            "Try increasing epsilon (relaxing privacy), providing more real training rows, "
            "or reviewing column type definitions in your schema."
        ),
    },
    {
        "question": "How do I use the SDK behind a corporate proxy?",
        "answer": (
            "Set the HTTPS_PROXY environment variable to your proxy URL. "
            "The Python SDK (httpx-based) respects standard proxy environment variables. "
            "For TypeScript/Node.js, use the https-proxy-agent package. "
            "For Go, configure http.DefaultTransport with your proxy settings."
        ),
    },
    {
        "question": "Can I use the SDK in a serverless environment (Lambda, Cloud Functions)?",
        "answer": (
            "Yes. Create a new AumOSClient instance per invocation rather than at module level "
            "to avoid connection pooling issues. The Python SDK's async client works well in "
            "Lambda with async handlers. Avoid keeping long-lived WebSocket connections."
        ),
    },
]


class IntegrationGuideGenerator:
    """Generates comprehensive integration guides and code examples for the AumOS SDK.

    Produces per-service integration guides in Markdown, multi-language code
    examples, troubleshooting FAQs, and migration guides between SDK versions.
    All output is plain text (Markdown) suitable for rendering in docs sites,
    READMEs, or interactive notebooks.
    """

    def generate_service_guide(
        self,
        service: str,
        language: str,
        include_troubleshooting: bool = True,
    ) -> dict[str, Any]:
        """Generate a complete integration guide for a specific service and language.

        Args:
            service: AumOS service area (agents | synthetic_data | authentication | ...).
            language: Target language (python | typescript | go | java).
            include_troubleshooting: Whether to append the troubleshooting FAQ.

        Returns:
            Guide dict with markdown_content, service, language, and code_example.

        Raises:
            ValueError: If service or language is not supported.
        """
        if language not in _SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{language}'. Supported: {sorted(_SUPPORTED_LANGUAGES)}"
            )
        if service not in _SUPPORTED_SERVICES:
            raise ValueError(
                f"Unsupported service '{service}'. Supported: {sorted(_SUPPORTED_SERVICES)}"
            )

        code_example = _CODE_EXAMPLES.get(service, {}).get(language, "# No example available.")
        markdown = self._render_service_guide(service, language, code_example, include_troubleshooting)

        return {
            "service": service,
            "language": language,
            "language_display": _LANGUAGE_DISPLAY.get(language, language),
            "code_example": code_example,
            "markdown_content": markdown,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "include_troubleshooting": include_troubleshooting,
        }

    def generate_quickstart_guide(self, language: str) -> dict[str, Any]:
        """Generate a minimal 5-minute quickstart guide for a language.

        Args:
            language: Target language (python | typescript | go | java).

        Returns:
            Quickstart guide dict with markdown_content and install_command.

        Raises:
            ValueError: If language is not supported.
        """
        if language not in _SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{language}'. Supported: {sorted(_SUPPORTED_LANGUAGES)}"
            )

        install_commands: dict[str, str] = {
            "python": "pip install aumos-sdk",
            "typescript": "npm install @aumos/sdk",
            "go": "go get github.com/aumos/aumos-sdk-go",
            "java": "<!-- Add to pom.xml: io.aumos:aumos-sdk:latest -->",
        }
        install_command = install_commands[language]
        auth_example = _CODE_EXAMPLES.get("authentication", {}).get(language, "")
        agents_example = _CODE_EXAMPLES.get("agents", {}).get(language, "")

        markdown = self._render_quickstart(language, install_command, auth_example, agents_example)

        return {
            "language": language,
            "language_display": _LANGUAGE_DISPLAY[language],
            "install_command": install_command,
            "markdown_content": markdown,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def get_troubleshooting_faq(
        self,
        filter_keywords: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Return troubleshooting FAQ entries, optionally filtered by keywords.

        Args:
            filter_keywords: Optional list of keywords to filter questions by.
                             Returns entries where any keyword appears in the question.

        Returns:
            List of FAQ entry dicts with question and answer.
        """
        if not filter_keywords:
            return list(_TROUBLESHOOTING_FAQ)

        lower_keywords = [kw.lower() for kw in filter_keywords]
        return [
            entry
            for entry in _TROUBLESHOOTING_FAQ
            if any(kw in entry["question"].lower() for kw in lower_keywords)
        ]

    def generate_migration_guide(
        self,
        from_version: str,
        to_version: str,
        breaking_changes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate a migration guide between two SDK versions.

        Args:
            from_version: Source SDK version string (e.g., '1.2.0').
            to_version: Target SDK version string (e.g., '2.0.0').
            breaking_changes: Optional list of breaking change dicts from OpenAPICodegen.

        Returns:
            Migration guide dict with markdown_content and upgrade_steps.
        """
        upgrade_steps: list[str] = [
            f"1. Update your dependency to version {to_version}.",
            "2. Run your existing test suite to identify breakages.",
            "3. Review the breaking changes listed below and update call sites.",
            "4. Update type annotations if using strict typing.",
            "5. Re-run your test suite to confirm all breakages are resolved.",
        ]

        markdown = self._render_migration_guide(from_version, to_version, breaking_changes or [], upgrade_steps)

        return {
            "from_version": from_version,
            "to_version": to_version,
            "breaking_changes": breaking_changes or [],
            "upgrade_steps": upgrade_steps,
            "markdown_content": markdown,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def list_available_guides(self) -> dict[str, Any]:
        """Return an index of all available integration guide combinations.

        Returns:
            Index dict with supported services, languages, and guide combinations.
        """
        combinations: list[dict[str, str]] = []
        for service in sorted(_SUPPORTED_SERVICES):
            for language in sorted(_SUPPORTED_LANGUAGES):
                has_example = service in _CODE_EXAMPLES and language in _CODE_EXAMPLES[service]
                combinations.append({
                    "service": service,
                    "language": language,
                    "has_code_example": str(has_example),
                })

        return {
            "supported_services": sorted(_SUPPORTED_SERVICES),
            "supported_languages": sorted(_SUPPORTED_LANGUAGES),
            "guide_combinations": combinations,
            "faq_entry_count": len(_TROUBLESHOOTING_FAQ),
        }

    # ------------------------------------------------------------------
    # Private rendering helpers
    # ------------------------------------------------------------------

    def _render_service_guide(
        self,
        service: str,
        language: str,
        code_example: str,
        include_troubleshooting: bool,
    ) -> str:
        """Render a service integration guide as Markdown.

        Args:
            service: Service area name.
            language: Target language name.
            code_example: Code snippet string.
            include_troubleshooting: Whether to include FAQ section.

        Returns:
            Markdown string.
        """
        lang_display = _LANGUAGE_DISPLAY.get(language, language)
        lang_fence = {"python": "python", "typescript": "typescript", "go": "go", "java": "java"}.get(language, language)

        lines: list[str] = [
            f"# AumOS SDK — {service.replace('_', ' ').title()} Integration Guide ({lang_display})",
            "",
            f"> Generated: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}",
            "",
            "## Overview",
            "",
            f"This guide shows how to integrate with the AumOS **{service}** service using "
            f"the {lang_display} SDK.",
            "",
            "## Installation",
            "",
        ]

        install_commands: dict[str, str] = {
            "python": "```bash\npip install aumos-sdk\n```",
            "typescript": "```bash\nnpm install @aumos/sdk\n```",
            "go": "```bash\ngo get github.com/aumos/aumos-sdk-go\n```",
            "java": "```xml\n<dependency>\n  <groupId>io.aumos</groupId>\n  <artifactId>aumos-sdk</artifactId>\n  <version>LATEST</version>\n</dependency>\n```",
        }
        lines.append(install_commands.get(language, ""))
        lines.extend([
            "",
            "## Authentication",
            "",
            "Set your API key via the `AUMOS_API_KEY` environment variable or pass it directly "
            "to the client constructor. See the [Authentication Guide](authentication-guide.md) "
            "for full details.",
            "",
            "## Code Example",
            "",
            f"```{lang_fence}",
            code_example.rstrip(),
            "```",
            "",
        ])

        if include_troubleshooting:
            lines.extend([
                "## Troubleshooting",
                "",
            ])
            for faq in _TROUBLESHOOTING_FAQ[:3]:
                lines.extend([
                    f"### {faq['question']}",
                    "",
                    faq["answer"],
                    "",
                ])

        lines.extend([
            "## Further Reading",
            "",
            "- [AumOS API Reference](https://docs.aumos.ai/api)",
            "- [SDK Changelog](https://github.com/aumos/aumos-sdk/blob/main/CHANGELOG.md)",
            "- [Support](mailto:support@aumos.ai)",
        ])

        return "\n".join(lines)

    def _render_quickstart(
        self,
        language: str,
        install_command: str,
        auth_example: str,
        agents_example: str,
    ) -> str:
        """Render a quickstart guide as Markdown.

        Args:
            language: Target language name.
            install_command: Package manager install command.
            auth_example: Authentication code snippet.
            agents_example: Agents code snippet.

        Returns:
            Markdown string.
        """
        lang_display = _LANGUAGE_DISPLAY.get(language, language)
        lang_fence = language if language != "typescript" else "typescript"

        lines: list[str] = [
            f"# AumOS SDK Quickstart — {lang_display}",
            "",
            "Get started with the AumOS SDK in 5 minutes.",
            "",
            "## Step 1: Install",
            "",
            f"```bash\n{install_command}\n```",
            "",
            "## Step 2: Configure Authentication",
            "",
            f"```{lang_fence}",
            auth_example.rstrip(),
            "```",
            "",
            "## Step 3: Make Your First API Call",
            "",
            f"```{lang_fence}",
            agents_example.rstrip(),
            "```",
            "",
            "## Next Steps",
            "",
            "- [Synthetic Data Generation Guide](synthetic-data-guide.md)",
            "- [Governance & Compliance](governance-guide.md)",
            "- [Full API Reference](https://docs.aumos.ai/api)",
        ]

        return "\n".join(lines)

    def _render_migration_guide(
        self,
        from_version: str,
        to_version: str,
        breaking_changes: list[dict[str, Any]],
        upgrade_steps: list[str],
    ) -> str:
        """Render a migration guide as Markdown.

        Args:
            from_version: Source version string.
            to_version: Target version string.
            breaking_changes: List of breaking change dicts.
            upgrade_steps: Ordered list of upgrade step strings.

        Returns:
            Markdown string.
        """
        lines: list[str] = [
            f"# AumOS SDK Migration Guide: v{from_version} → v{to_version}",
            "",
            f"> Generated: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}",
            "",
            "## Upgrade Steps",
            "",
        ]
        for step in upgrade_steps:
            lines.append(step)
        lines.append("")

        if breaking_changes:
            lines.extend([
                "## Breaking Changes",
                "",
                f"This version contains **{len(breaking_changes)}** breaking change(s).",
                "",
            ])
            for change in breaking_changes:
                if "removed_paths" in change:
                    for path in change["removed_paths"]:
                        lines.append(f"- **Removed path**: `{path}`")
                elif "removed_methods" in change:
                    for item in change["removed_methods"]:
                        lines.append(f"- **Removed method**: `{item.get('method')} {item.get('path')}`")
                elif "new_required_parameters" in change:
                    for item in change["new_required_parameters"]:
                        lines.append(
                            f"- **New required parameter**: `{item.get('parameter')}` "
                            f"on `{item.get('method')} {item.get('path')}`"
                        )
            lines.append("")
        else:
            lines.extend([
                "## Breaking Changes",
                "",
                "No breaking changes in this release.",
                "",
            ])

        lines.extend([
            "## Support",
            "",
            "If you encounter issues upgrading, contact support@aumos.ai "
            "or open an issue on [GitHub](https://github.com/aumos/aumos-sdk/issues).",
        ])

        return "\n".join(lines)
