"""Python async client generator for the AumOS SDK.

Generates idiomatic Python async client code from an OpenAPI spec for embedding
in generated SDK stubs. The hand-crafted `client.py` wraps these stubs; this
module drives the `_generated/` code layer. Also provides utilities for
pagination helpers, streaming, retry/backoff configuration, and type stub generation.
"""

from typing import Any

# Supported Python primitive type mappings from OpenAPI types
_OPENAPI_TO_PYTHON_TYPES: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict[str, Any]",
}

# Default retry configuration
_DEFAULT_MAX_RETRIES: int = 3
_DEFAULT_BACKOFF_FACTOR: float = 0.5
_DEFAULT_RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

# Pydantic v2 field serialization alias template
_FIELD_ALIAS_TEMPLATE: str = '    {field_name}: {python_type} = Field(alias="{wire_name}")'

# Async resource method template
_ASYNC_METHOD_TEMPLATE: str = '''\
    async def {method_name}(self, {params}) -> {return_type}:
        """{docstring}"""
        response = await self._client.request(
            method="{http_method}",
            url=f"{url_template}",
            {request_kwargs}
        )
        return {return_type}.model_validate(response)
'''


class PythonAsyncClientGenerator:
    """Generates Python async client code from an OpenAPI specification.

    Produces Pydantic v2 model classes, httpx-based async resource classes,
    pagination helpers, streaming support, and retry configuration stubs
    for inclusion in the AumOS Python SDK's `_generated/` directory.
    """

    def __init__(
        self,
        package_name: str = "aumos_sdk._generated",
        base_client_import: str = "from aumos_sdk._http import AsyncHTTPClient",
    ) -> None:
        """Initialise the Python client generator.

        Args:
            package_name: Python package name for generated code.
            base_client_import: Import statement for the base HTTP client class.
        """
        self._package_name = package_name
        self._base_client_import = base_client_import

    def generate_model(
        self,
        model_name: str,
        schema: dict[str, Any],
        use_aliases: bool = True,
    ) -> str:
        """Generate a Pydantic v2 model class from an OpenAPI schema.

        Args:
            model_name: Python class name for the model (PascalCase).
            schema: OpenAPI JSON schema dict.
            use_aliases: When True, generate camelCase wire aliases.

        Returns:
            Python source string for the Pydantic model class.
        """
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))
        description = schema.get("description", f"AumOS {model_name} model.")

        lines: list[str] = [
            f'class {model_name}(BaseModel):',
            f'    """{description}"""',
            "",
        ]

        if not properties:
            lines.append("    pass")
        else:
            for prop_name, prop_schema in properties.items():
                python_type = self._resolve_type(prop_schema)
                is_required = prop_name in required_fields
                snake_name = self._to_snake_case(prop_name)

                if use_aliases and snake_name != prop_name:
                    if is_required:
                        lines.append(
                            f'    {snake_name}: {python_type} = Field(alias="{prop_name}")'
                        )
                    else:
                        lines.append(
                            f'    {snake_name}: {python_type} | None = Field(None, alias="{prop_name}")'
                        )
                else:
                    if is_required:
                        lines.append(f"    {snake_name}: {python_type}")
                    else:
                        lines.append(f"    {snake_name}: {python_type} | None = None")

            if use_aliases:
                lines.extend([
                    "",
                    "    model_config = ConfigDict(populate_by_name=True)",
                ])

        lines.append("")
        return "\n".join(lines)

    def generate_resource_class(
        self,
        resource_name: str,
        operations: list[dict[str, Any]],
    ) -> str:
        """Generate an async resource class for a group of API operations.

        Args:
            resource_name: Resource class name (e.g., 'AgentsResource').
            operations: List of operation dicts from OpenAPICodegen.list_all_operations.

        Returns:
            Python source string for the async resource class.
        """
        lines: list[str] = [
            f"class {resource_name}:",
            f'    """Async resource for {resource_name.replace("Resource", "").lower()} operations."""',
            "",
            "    def __init__(self, client: AsyncHTTPClient) -> None:",
            '        """Initialise with the base HTTP client.',
            "",
            "        Args:",
            "            client: Authenticated HTTP client instance.",
            '        """',
            "        self._client = client",
            "",
        ]

        for operation in operations:
            method_source = self._generate_operation_method(operation)
            lines.append(method_source)

        return "\n".join(lines)

    def generate_pagination_helper(self) -> str:
        """Generate a generic async pagination helper for list endpoints.

        Returns:
            Python source string for the paginate() async generator.
        """
        return '''\
async def paginate(
    resource_method,
    *args: Any,
    page_size: int = 20,
    max_pages: int | None = None,
    **kwargs: Any,
):
    """Async generator that paginates through all results from a list method.

    Args:
        resource_method: Async resource method returning a PageResponse.
        *args: Positional arguments forwarded to the resource method.
        page_size: Number of items per page.
        max_pages: Optional limit on the number of pages to fetch.
        **kwargs: Keyword arguments forwarded to the resource method.

    Yields:
        Individual items from each page.
    """
    page = 1
    pages_fetched = 0
    while True:
        response = await resource_method(*args, page=page, page_size=page_size, **kwargs)
        for item in response.items:
            yield item
        pages_fetched += 1
        if max_pages is not None and pages_fetched >= max_pages:
            break
        if page >= response.pages:
            break
        page += 1
'''

    def generate_retry_config(
        self,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_factor: float = _DEFAULT_BACKOFF_FACTOR,
        retry_statuses: frozenset[int] = _DEFAULT_RETRY_STATUSES,
    ) -> str:
        """Generate a retry configuration dataclass for the async HTTP client.

        Args:
            max_retries: Maximum number of retry attempts.
            backoff_factor: Exponential backoff multiplier in seconds.
            retry_statuses: Set of HTTP status codes that trigger a retry.

        Returns:
            Python source string for the RetryConfig dataclass.
        """
        statuses_repr = repr(sorted(retry_statuses))
        return f'''\
@dataclass
class RetryConfig:
    """Retry and backoff configuration for the AumOS async HTTP client.

    Attributes:
        max_retries: Maximum number of retry attempts before raising.
        backoff_factor: Wait = backoff_factor * (2 ** attempt) seconds.
        retry_statuses: HTTP status codes that trigger an automatic retry.
    """

    max_retries: int = {max_retries}
    backoff_factor: float = {backoff_factor}
    retry_statuses: frozenset[int] = field(default_factory=lambda: frozenset({statuses_repr}))

    def should_retry(self, attempt: int, status_code: int) -> bool:
        """Determine whether a request should be retried.

        Args:
            attempt: Zero-based attempt index.
            status_code: HTTP response status code.

        Returns:
            True if the request should be retried.
        """
        return attempt < self.max_retries and status_code in self.retry_statuses

    def wait_seconds(self, attempt: int) -> float:
        """Calculate the wait time before the next retry attempt.

        Args:
            attempt: Zero-based attempt index.

        Returns:
            Seconds to wait before retrying.
        """
        return self.backoff_factor * (2 ** attempt)
'''

    def generate_module_header(self, description: str = "") -> str:
        """Generate the standard module header for a generated Python file.

        Args:
            description: Module description for the docstring.

        Returns:
            Python source string with module docstring and standard imports.
        """
        return f'''\
"""Generated AumOS Python SDK module. DO NOT EDIT — regenerate via `make generate-python`.

{description or "Auto-generated from the AumOS OpenAPI specification."}
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx
from pydantic import BaseModel, ConfigDict, Field

from aumos_sdk.exceptions import AumOSAPIError
{self._base_client_import}
'''

    def generate_all_models(
        self,
        spec: dict[str, Any],
    ) -> str:
        """Generate all Pydantic model classes from an OpenAPI spec's components.

        Args:
            spec: OpenAPI spec dict with components.schemas.

        Returns:
            Python source string with all model class definitions.
        """
        schemas = spec.get("components", {}).get("schemas", {})
        header = self.generate_module_header("Pydantic v2 models generated from AumOS OpenAPI spec.")
        model_sources: list[str] = [header]

        for schema_name, schema in sorted(schemas.items()):
            model_source = self.generate_model(schema_name, schema)
            model_sources.append(model_source)

        return "\n".join(model_sources)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_type(self, schema: dict[str, Any]) -> str:
        """Resolve an OpenAPI schema to a Python type annotation string.

        Args:
            schema: OpenAPI property schema dict.

        Returns:
            Python type annotation string.
        """
        ref = schema.get("$ref", "")
        if ref:
            return ref.split("/")[-1]

        schema_type = schema.get("type", "object")
        if schema_type == "array":
            item_schema = schema.get("items", {})
            item_type = self._resolve_type(item_schema)
            return f"list[{item_type}]"

        return _OPENAPI_TO_PYTHON_TYPES.get(schema_type, "Any")

    def _to_snake_case(self, name: str) -> str:
        """Convert a camelCase or PascalCase name to snake_case.

        Args:
            name: camelCase or PascalCase identifier.

        Returns:
            snake_case identifier.
        """
        import re
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
        return name.lower()

    def _generate_operation_method(self, operation: dict[str, Any]) -> str:
        """Generate an async method stub for a single API operation.

        Args:
            operation: Operation dict from OpenAPICodegen.list_all_operations.

        Returns:
            Python source string for the async method.
        """
        method_name = self._derive_method_name(operation)
        http_method = operation.get("method", "GET")
        path = operation.get("path", "/")
        summary = operation.get("summary", f"Call {http_method} {path}.")
        has_body = operation.get("has_request_body", False)

        params: list[str] = ["self"]
        if "{" in path:
            import re
            path_params = re.findall(r"\{(\w+)\}", path)
            params.extend(f"{p}: str" for p in path_params)

        if has_body:
            params.append("body: dict[str, Any]")

        params_str = ", ".join(params)
        url_template = path.replace("{", "{")

        request_kwargs = "json=body," if has_body else ""

        return f'''\
    async def {method_name}({params_str}) -> dict[str, Any]:
        """{summary}"""
        response = await self._client.request(
            method="{http_method}",
            url=f"{url_template}",
            {request_kwargs}
        )
        return response

'''

    def _derive_method_name(self, operation: dict[str, Any]) -> str:
        """Derive a Python method name from an operation's operationId or path/method.

        Args:
            operation: Operation dict.

        Returns:
            snake_case method name string.
        """
        operation_id = operation.get("operation_id", "")
        if operation_id:
            return self._to_snake_case(operation_id)

        method = operation.get("method", "GET").lower()
        path = operation.get("path", "").strip("/").replace("/", "_").replace("{", "").replace("}", "")
        return f"{method}_{path}" or "call"
