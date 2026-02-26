.PHONY: all generate generate-python generate-typescript generate-go generate-java \
        test test-python test-typescript test-go test-java \
        lint lint-python lint-typescript lint-go lint-java \
        build build-python build-typescript \
        clean

# ---------------------------------------------------------------------------
# Code generation from OpenAPI spec
# ---------------------------------------------------------------------------

OPENAPI_GENERATOR := openapi-generator-cli
SPEC := openapi/aumos-api.yaml

generate: generate-python generate-typescript generate-go generate-java

generate-python:
	$(OPENAPI_GENERATOR) generate \
		-i $(SPEC) \
		-g python \
		-o python/src/aumos_sdk/_generated \
		--additional-properties=packageName=aumos_sdk._generated,generateSourceCodeOnly=true

generate-typescript:
	$(OPENAPI_GENERATOR) generate \
		-i $(SPEC) \
		-g typescript-fetch \
		-o typescript/src/_generated \
		--additional-properties=npmName=@aumos/sdk-generated,typescriptThreePlus=true

generate-go:
	$(OPENAPI_GENERATOR) generate \
		-i $(SPEC) \
		-g go \
		-o go/_generated \
		--additional-properties=packageName=aumos,moduleName=go.aumos.io/sdk

generate-java:
	$(OPENAPI_GENERATOR) generate \
		-i $(SPEC) \
		-g java \
		-o java \
		--additional-properties=groupId=io.aumos,artifactId=aumos-sdk,library=okhttp-gson

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test: test-python test-typescript test-go test-java

test-python:
	@echo "==> Testing Python SDK"
	cd python && python -m pytest tests/ -v

test-typescript:
	@echo "==> Testing TypeScript SDK"
	cd typescript && npm test

test-go:
	@echo "==> Testing Go SDK"
	cd go && go test ./...

test-java:
	@echo "==> Testing Java SDK"
	cd java && mvn test

# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

lint: lint-python lint-typescript lint-go lint-java

lint-python:
	@echo "==> Linting Python SDK"
	cd python && python -m ruff check src/ && python -m mypy src/

lint-typescript:
	@echo "==> Linting TypeScript SDK"
	cd typescript && npm run typecheck && npm run lint

lint-go:
	@echo "==> Linting Go SDK"
	cd go && go vet ./... && gofmt -l .

lint-java:
	@echo "==> Linting Java SDK"
	cd java && mvn checkstyle:check

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

build: build-python build-typescript

build-python:
	@echo "==> Building Python SDK"
	cd python && python -m build

build-typescript:
	@echo "==> Building TypeScript SDK"
	cd typescript && npm run build

# ---------------------------------------------------------------------------
# Install dev dependencies
# ---------------------------------------------------------------------------

install: install-python install-typescript install-go

install-python:
	cd python && pip install -e ".[dev]"

install-typescript:
	cd typescript && npm install

install-go:
	cd go && go mod download

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

clean:
	rm -rf python/dist python/build python/src/aumos_sdk/_generated
	rm -rf typescript/dist typescript/node_modules typescript/src/_generated
	rm -rf go/_generated
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
