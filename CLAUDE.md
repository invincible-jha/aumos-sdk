# CLAUDE.md — aumos-sdk

## Purpose

Customer-facing SDKs for the AumOS Enterprise platform.
Supports Python, TypeScript, Go, and Java with auto-generation from a master OpenAPI spec.

## Architecture

```
openapi/        Master OpenAPI 3.1 spec + codegen configuration
python/         Python async SDK (primary, hand-crafted)
typescript/     TypeScript SDK (primary, hand-crafted)
go/             Go SDK (idiomatic, hand-crafted)
java/           Java SDK (OkHttp + Gson)
examples/       Language-specific quickstart scripts
```

## Design Principles

1. **OpenAPI-first**: All types derive from `openapi/aumos-api.yaml`
2. **Hand-crafted over pure codegen**: Generated stubs are a starting point; the
   published SDKs are curated and ergonomic
3. **Async by default**: Python (asyncio), TypeScript (Promise), Go (context)
4. **Minimal dependencies**: Each SDK depends only on what is strictly necessary
5. **Structured error hierarchy**: Every SDK has a parallel exception tree rooted
   at a base SDK error type

## Language-specific Guidelines

### Python

- Requires Python 3.11+
- Uses `httpx.AsyncClient` for HTTP
- Pydantic v2 models with camelCase aliases for wire format
- Type hints required on every function signature
- No `any` typing (use `dict[str, Any]` with proper guards)
- Auth strategy pattern: `AuthStrategy` ABC → `ApiKeyAuth | BearerTokenAuth`

### TypeScript

- Requires Node.js 18+ (native Fetch API)
- Strict mode, no `any`
- Named exports only
- Branded UUID type for type safety
- Resource pattern: `AgentsResource`, `RunsResource`, etc. as instance properties

### Go

- Idiomatic Go: unexported struct fields, functional options (`WithAPIKey`, etc.)
- Services pattern: `client.Agents`, `client.Runs`, `client.Models`, `client.Governance`
- All methods accept `context.Context` as the first argument
- `APIError` implements `error` interface

### Java

- Java 17+, uses `sealed` and `switch` expressions where appropriate
- Builder pattern for client construction
- OkHttp for HTTP, Gson for JSON
- `AutoCloseable` — use try-with-resources or call `close()`

## Codegen Pipeline

```bash
# Install
npm install -g @openapitools/openapi-generator-cli

# Regenerate all
make generate

# Individual
make generate-python
make generate-typescript
make generate-go
make generate-java
```

Generated stubs go into `{language}/src/.../\_generated/` and must NOT be
directly imported by user code — the hand-crafted client wraps them.

## Release Checklist

- [ ] Bump version in: `python/pyproject.toml`, `typescript/package.json`,
      `go/go.mod` (tag), `java/pom.xml`
- [ ] Update `CHANGELOG.md`
- [ ] Run `make test` — all suites green
- [ ] Run `make lint` — no warnings
- [ ] Publish Python to PyPI: `make build-python && twine upload`
- [ ] Publish TypeScript to npm: `cd typescript && npm publish`
- [ ] Tag the release: `git tag sdk/v1.x.x && git push --tags`

## License

Apache 2.0 — no GPL/AGPL dependencies permitted.
