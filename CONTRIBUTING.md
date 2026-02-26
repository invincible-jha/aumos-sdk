# Contributing to aumos-sdk

Thank you for contributing to the AumOS SDK. This guide covers all four languages.

## Getting Started

1. Fork the repository (external contributors) or clone directly (AumOS team)
2. Create a feature branch from `main`: `git checkout -b feature/your-feature`
3. Make changes following the per-language standards below
4. Run tests and linting for affected languages
5. Submit a pull request targeting `main`

## Development Setup

### Python

```bash
cd python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### TypeScript

```bash
cd typescript
npm install
```

### Go

```bash
cd go
go mod download
```

### Java

```bash
cd java
mvn install -DskipTests
```

## Running Tests

```bash
# All languages
make test

# Individual
make test-python
make test-typescript
make test-go
make test-java
```

## Code Standards

### Python

- Type hints on every function signature
- Pydantic for all data models
- `async`/`await` for all I/O
- Google-style docstrings on all public symbols
- Max line length: 120

### TypeScript

- Strict mode — no `any`
- Named exports only
- `readonly` where fields are not mutated

### Go

- `context.Context` as first parameter on all methods
- Functional options for `Client` configuration
- Document all exported symbols with godoc comments

### Java

- Java 17 features where appropriate
- Builder pattern for complex objects
- Javadoc on all public methods

## Updating the OpenAPI Spec

If you change `openapi/aumos-api.yaml`:

1. Validate the spec: `npx swagger-cli validate openapi/aumos-api.yaml`
2. Run `make generate` to regenerate stubs
3. Update hand-crafted SDK code to match any new endpoints/models
4. Update the CHANGELOG

## License Compliance

All dependencies must be Apache 2.0, MIT, BSD-2, BSD-3, or ISC.
No GPL or AGPL dependencies are permitted.

```bash
# Python
pip-licenses --packages $(pip freeze | cut -d= -f1 | tr '\n' ',')

# Node
npx license-checker --summary
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(python): add BearerTokenAuth token refresh support
fix(typescript): handle empty response body on 204
docs(go): add WaitForRun example to README
chore: bump openapi-generator-cli to 7.3.0
```

## PR Process

1. All CI checks must pass (lint, typecheck, test)
2. At least one reviewer from `@aumos/platform-team`
3. Squash merge — keep `main` history clean
4. Delete your branch after merge
