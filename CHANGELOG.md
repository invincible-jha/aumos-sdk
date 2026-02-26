# Changelog

All notable changes to the AumOS SDK are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] — 2026-02-26

### Added

- Python SDK with full async support (`AumOSClient`, agents, runs, models, governance)
- TypeScript/JavaScript SDK targeting Node.js 18+ (native Fetch API)
- Go SDK with idiomatic functional-options pattern
- Java SDK using OkHttp and Gson, Java 17+
- Master OpenAPI 3.1 spec (`openapi/aumos-api.yaml`) covering all v1 endpoints
- Code-generation configuration for openapi-generator-cli
- Quickstart examples for Python and TypeScript
- Makefile with generate, test, lint, and build targets for all languages

### Python SDK

- `AumOSClient` async context manager with connection pooling (httpx)
- `AgentsResource` — list, create, get, update, delete, create_run, list_runs, wait_for_run
- `RunsResource` — get
- `ModelsResource` — list, get
- `GovernanceResource` — list_policies, list_audit_logs
- Pydantic v2 models with camelCase aliases for wire format
- `ApiKeyAuth` and `BearerTokenAuth` with optional token refresh callbacks
- Structured exception hierarchy: `AumOSError` → `AumOSAPIError` → specific errors
- Automatic retry with exponential backoff for 429/5xx responses

### TypeScript SDK

- `AumOSClient` with `AgentsResource`, `RunsResource`, `ModelsResource`, `GovernanceResource`
- Branded UUID and ISODateTime types for improved type safety
- Full `AumOSError` exception hierarchy with `AumOSAuthenticationError`, `AumOSNotFoundError`, etc.
- Dual ESM/CJS build via tsup
- Strict TypeScript with no `any`

### Go SDK

- `Client` with `Agents`, `Runs`, `Models`, `Governance` service fields
- `WithAPIKey`, `WithBaseURL`, `WithTimeout`, `WithMaxRetries`, `WithHTTPClient` options
- `APIError` type with `StatusCode`, `ErrorCode`, `Message`, `RequestID`
- `IsTerminal()` and `Succeeded()` helpers on `Run`

### Java SDK

- `AumOSClient` with builder pattern and `AutoCloseable`
- Nested resource classes: `AgentsResource`, `RunsResource`, `ModelsResource`, `GovernanceResource`
- Exception types: `AumOSAPIException`, `AumOSNetworkException`, `AumOSConfigurationException`
- `waitForRun` with configurable poll interval and max wait

[Unreleased]: https://github.com/aumos-enterprise/aumos-sdk/compare/sdk/v1.0.0...HEAD
[1.0.0]: https://github.com/aumos-enterprise/aumos-sdk/releases/tag/sdk/v1.0.0
