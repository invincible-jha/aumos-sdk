"""OpenAPI code generation orchestrator for the AumOS SDK.

Fetches the master AumOS OpenAPI specification, validates it, detects breaking
changes against a previous version, orchestrates per-language code generation,
and manages SDK versioning. Acts as the build-time driver for the codegen
pipeline defined in the SDK Makefile.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# Supported code generation targets
_SUPPORTED_TARGETS: frozenset[str] = frozenset({"python", "typescript", "go", "java"})

# OpenAPI HTTP method set
_HTTP_METHODS: frozenset[str] = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})

# Breaking change categories
_BREAKING_REMOVALS: str = "removed_paths"
_BREAKING_METHOD_REMOVALS: str = "removed_methods"
_BREAKING_REQUIRED_ADDED: str = "new_required_parameters"
_BREAKING_TYPE_CHANGES: str = "schema_type_changes"


class OpenAPICodegen:
    """Orchestrates OpenAPI-to-SDK code generation across all supported languages.

    Fetches and caches the master OpenAPI spec, validates its structure,
    compares versions for breaking changes, and drives per-language generation.
    The generated stub files are written to the `_generated/` subdirectory of
    each language SDK — they are not imported directly by user code.
    """

    def __init__(
        self,
        spec_url: str,
        output_root: str | Path,
        http_timeout: float = 30.0,
    ) -> None:
        """Initialise the codegen orchestrator.

        Args:
            spec_url: URL to fetch the master OpenAPI 3.x specification.
            output_root: Root directory containing language SDK directories.
            http_timeout: HTTP request timeout in seconds.
        """
        self._spec_url = spec_url
        self._output_root = Path(output_root)
        self._http_timeout = http_timeout
        self._cached_spec: dict[str, Any] | None = None

    def fetch_spec(self) -> dict[str, Any]:
        """Fetch the OpenAPI specification from the configured URL.

        Returns:
            Parsed OpenAPI spec dict.

        Raises:
            RuntimeError: If the spec cannot be fetched or parsed.
        """
        if self._cached_spec is not None:
            return self._cached_spec

        try:
            with httpx.Client(timeout=self._http_timeout) as client:
                response = client.get(self._spec_url)
                response.raise_for_status()
                self._cached_spec = response.json()
                return self._cached_spec
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch OpenAPI spec from {self._spec_url}: {exc}") from exc

    def load_spec_from_file(self, spec_path: str | Path) -> dict[str, Any]:
        """Load and cache the OpenAPI specification from a local file.

        Args:
            spec_path: Path to the YAML or JSON OpenAPI file.

        Returns:
            Parsed OpenAPI spec dict.

        Raises:
            FileNotFoundError: If the spec file does not exist.
            ValueError: If the file cannot be parsed.
        """
        path = Path(spec_path)
        if not path.exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {path}")

        content = path.read_text(encoding="utf-8")
        try:
            if path.suffix in (".yaml", ".yml"):
                # Minimal YAML parsing for common scalar types without requiring PyYAML
                self._cached_spec = self._parse_yaml_simple(content)
            else:
                self._cached_spec = json.loads(content)
        except Exception as exc:
            raise ValueError(f"Failed to parse OpenAPI spec at {path}: {exc}") from exc

        return self._cached_spec

    def validate_spec(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Validate the structural integrity of an OpenAPI 3.x specification.

        Checks for the presence of required top-level keys (openapi, info, paths)
        and verifies that the version string starts with '3.'.

        Args:
            spec: OpenAPI spec dict to validate.

        Returns:
            Validation result dict with valid (bool), errors, and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        for required_key in ("openapi", "info", "paths"):
            if required_key not in spec:
                errors.append(f"Missing required top-level field: '{required_key}'")

        openapi_version = spec.get("openapi", "")
        if not str(openapi_version).startswith("3."):
            errors.append(
                f"Expected OpenAPI 3.x, got '{openapi_version}'. Only OpenAPI 3.x is supported."
            )

        info = spec.get("info", {})
        if not info.get("title"):
            warnings.append("Missing 'info.title' — SDK generator may produce unnamed packages.")
        if not info.get("version"):
            warnings.append("Missing 'info.version' — SDK versioning may be incorrect.")

        paths = spec.get("paths", {})
        if not paths:
            warnings.append("No paths defined in spec — generated SDK will have no endpoints.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "path_count": len(paths),
            "info_title": info.get("title", ""),
            "info_version": info.get("version", ""),
        }

    def detect_breaking_changes(
        self,
        previous_spec: dict[str, Any],
        current_spec: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare two OpenAPI spec versions and identify breaking changes.

        Breaking changes include: removed paths, removed HTTP methods on existing
        paths, new required parameters on existing operations, and schema type
        changes on existing response/request schemas.

        Args:
            previous_spec: The previous (released) OpenAPI spec dict.
            current_spec: The new (candidate) OpenAPI spec dict.

        Returns:
            Breaking changes report dict with per-category lists and has_breaking_changes flag.
        """
        prev_paths = previous_spec.get("paths", {})
        curr_paths = current_spec.get("paths", {})

        removed_paths: list[str] = []
        removed_methods: list[dict[str, str]] = []
        new_required_parameters: list[dict[str, Any]] = []
        schema_type_changes: list[dict[str, Any]] = []

        for path, prev_path_item in prev_paths.items():
            if path not in curr_paths:
                removed_paths.append(path)
                continue

            curr_path_item = curr_paths[path]

            for method in _HTTP_METHODS:
                prev_op = prev_path_item.get(method)
                curr_op = curr_path_item.get(method)

                if prev_op is not None and curr_op is None:
                    removed_methods.append({"path": path, "method": method.upper()})
                    continue

                if prev_op is None or curr_op is None:
                    continue

                prev_params = {p["name"]: p for p in prev_op.get("parameters", []) if "name" in p}
                curr_params = {p["name"]: p for p in curr_op.get("parameters", []) if "name" in p}

                for param_name, curr_param in curr_params.items():
                    if curr_param.get("required") and param_name not in prev_params:
                        new_required_parameters.append({
                            "path": path,
                            "method": method.upper(),
                            "parameter": param_name,
                        })

                prev_schema = self._extract_response_schema(prev_op)
                curr_schema = self._extract_response_schema(curr_op)
                if prev_schema and curr_schema:
                    if prev_schema.get("type") != curr_schema.get("type"):
                        schema_type_changes.append({
                            "path": path,
                            "method": method.upper(),
                            "previous_type": prev_schema.get("type"),
                            "current_type": curr_schema.get("type"),
                        })

        all_breaking: list[dict[str, Any]] = []
        if removed_paths:
            all_breaking.append({_BREAKING_REMOVALS: removed_paths})
        if removed_methods:
            all_breaking.append({_BREAKING_METHOD_REMOVALS: removed_methods})
        if new_required_parameters:
            all_breaking.append({_BREAKING_REQUIRED_ADDED: new_required_parameters})
        if schema_type_changes:
            all_breaking.append({_BREAKING_TYPE_CHANGES: schema_type_changes})

        has_breaking = bool(removed_paths or removed_methods or new_required_parameters or schema_type_changes)

        return {
            "has_breaking_changes": has_breaking,
            "removed_paths": removed_paths,
            "removed_methods": removed_methods,
            "new_required_parameters": new_required_parameters,
            "schema_type_changes": schema_type_changes,
            "breaking_change_count": (
                len(removed_paths)
                + len(removed_methods)
                + len(new_required_parameters)
                + len(schema_type_changes)
            ),
            "compared_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def extract_sdk_version_from_spec(self, spec: dict[str, Any]) -> str:
        """Extract the API version from an OpenAPI spec for SDK versioning.

        Args:
            spec: OpenAPI spec dict.

        Returns:
            Version string from info.version, defaulting to '0.0.0'.
        """
        return spec.get("info", {}).get("version", "0.0.0")

    def list_all_operations(self, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract all operations from the spec for documentation and SDK generation.

        Args:
            spec: OpenAPI spec dict.

        Returns:
            List of operation dicts with path, method, operationId, tags, and summary.
        """
        operations: list[dict[str, Any]] = []
        for path, path_item in spec.get("paths", {}).items():
            for method in _HTTP_METHODS:
                operation = path_item.get(method)
                if operation is None:
                    continue
                operations.append({
                    "path": path,
                    "method": method.upper(),
                    "operation_id": operation.get("operationId", ""),
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "tags": operation.get("tags", []),
                    "deprecated": operation.get("deprecated", False),
                    "requires_auth": bool(operation.get("security")),
                    "parameter_count": len(operation.get("parameters", [])),
                    "has_request_body": bool(operation.get("requestBody")),
                })
        return sorted(operations, key=lambda o: (o["path"], o["method"]))

    def generate_codegen_config(
        self,
        target: str,
        spec: dict[str, Any],
        extra_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build an openapi-generator-cli compatible config for a target language.

        Args:
            target: Language target (python | typescript | go | java).
            spec: OpenAPI spec dict (used to read version/package name).
            extra_options: Optional additional generator options.

        Returns:
            Config dict ready to serialize as codegen-config.yaml.

        Raises:
            ValueError: If target is not supported.
        """
        if target not in _SUPPORTED_TARGETS:
            raise ValueError(
                f"Unsupported target '{target}'. Supported: {sorted(_SUPPORTED_TARGETS)}"
            )

        api_version = self.extract_sdk_version_from_spec(spec)
        output_subdir = self._output_root / target / "src" / "_generated"

        base_configs: dict[str, dict[str, Any]] = {
            "python": {
                "generatorName": "python",
                "outputDir": str(output_subdir),
                "packageName": "aumos_sdk._generated",
                "packageVersion": api_version,
                "additionalProperties": {
                    "asyncioMode": True,
                    "generateSourceCodeOnly": True,
                },
            },
            "typescript": {
                "generatorName": "typescript-fetch",
                "outputDir": str(output_subdir),
                "npmName": "@aumos/sdk-generated",
                "npmVersion": api_version,
                "additionalProperties": {
                    "supportsES6": True,
                    "typescriptThreePlus": True,
                },
            },
            "go": {
                "generatorName": "go",
                "outputDir": str(output_subdir),
                "packageName": "generated",
                "additionalProperties": {
                    "isGoSubmodule": True,
                    "structPrefix": True,
                },
            },
            "java": {
                "generatorName": "java",
                "outputDir": str(output_subdir),
                "groupId": "io.aumos",
                "artifactId": "aumos-sdk-generated",
                "artifactVersion": api_version,
                "library": "okhttp-gson",
                "additionalProperties": {
                    "java8": True,
                    "dateLibrary": "java8",
                },
            },
        }

        config = base_configs[target]
        if extra_options:
            config["additionalProperties"] = {
                **config.get("additionalProperties", {}),
                **extra_options,
            }

        return config

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_response_schema(self, operation: dict[str, Any]) -> dict[str, Any] | None:
        """Extract the primary 200 response JSON schema from an operation.

        Args:
            operation: OpenAPI operation dict.

        Returns:
            JSON schema dict or None if no 200 JSON response defined.
        """
        responses = operation.get("responses", {})
        ok_response = responses.get("200", responses.get("201", {}))
        content = ok_response.get("content", {})
        json_content = content.get("application/json", {})
        return json_content.get("schema") or None

    def _parse_yaml_simple(self, content: str) -> dict[str, Any]:
        """Minimal YAML-like parser for simple flat key-value structures.

        This is not a full YAML parser — it handles only the subset of YAML
        used in simple OpenAPI metadata reading. For full spec parsing, use
        PyYAML or the json format.

        Args:
            content: YAML string content.

        Returns:
            Parsed dict (best-effort, top-level only).
        """
        result: dict[str, Any] = {}
        for line in content.splitlines():
            if ":" in line and not line.strip().startswith("#"):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key and value:
                    result[key] = value
        return result
