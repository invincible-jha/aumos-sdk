"""TypeScript SDK client generator for the AumOS SDK.

Generates idiomatic TypeScript client code from an OpenAPI specification.
Produces strict-mode TypeScript types, fetch-based resource classes, branded
UUID types, error class hierarchies, and index barrel exports for the
AumOS TypeScript SDK's `_generated/` layer.
"""

from typing import Any

# OpenAPI type → TypeScript type mappings
_OPENAPI_TO_TYPESCRIPT_TYPES: dict[str, str] = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "array": "Array",
    "object": "Record<string, unknown>",
}

# TypeScript format-specific type overrides
_FORMAT_OVERRIDES: dict[str, str] = {
    "uuid": "UUID",
    "date-time": "string",  # ISO8601 string
    "date": "string",
    "email": "string",
    "uri": "string",
    "binary": "Blob",
}

# Generated file header
_TS_HEADER: str = """\
/**
 * Generated AumOS TypeScript SDK types. DO NOT EDIT.
 * Regenerate via: make generate-typescript
 */

/* eslint-disable */
"""


class TypeScriptClientGenerator:
    """Generates TypeScript SDK client code from an OpenAPI specification.

    Produces strict-mode TypeScript interfaces, branded UUID types, fetch-based
    async resource classes, typed error classes, and barrel index exports.
    All output targets TypeScript strict mode with no 'any' types.
    """

    def __init__(
        self,
        api_base_url: str = "https://api.aumos.ai",
        sdk_package_name: str = "@aumos/sdk",
    ) -> None:
        """Initialise the TypeScript generator.

        Args:
            api_base_url: Default base URL for the generated client.
            sdk_package_name: npm package name for import references.
        """
        self._api_base_url = api_base_url
        self._sdk_package_name = sdk_package_name

    def generate_interface(
        self,
        interface_name: str,
        schema: dict[str, Any],
        export: bool = True,
    ) -> str:
        """Generate a TypeScript interface from an OpenAPI schema.

        Args:
            interface_name: TypeScript interface name (PascalCase).
            schema: OpenAPI JSON schema dict.
            export: Whether to prefix the interface with 'export'.

        Returns:
            TypeScript source string for the interface definition.
        """
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))
        description = schema.get("description", f"AumOS {interface_name} type.")

        export_prefix = "export " if export else ""
        lines: list[str] = [
            f"/** {description} */",
            f"{export_prefix}interface {interface_name} {{",
        ]

        for prop_name, prop_schema in properties.items():
            ts_type = self._resolve_type(prop_schema)
            is_required = prop_name in required_fields
            optional_marker = "" if is_required else "?"
            prop_description = prop_schema.get("description", "")

            if prop_description:
                lines.append(f"  /** {prop_description} */")
            lines.append(f"  readonly {prop_name}{optional_marker}: {ts_type};")

        lines.append("}")
        return "\n".join(lines)

    def generate_branded_uuid(self, brand_name: str) -> str:
        """Generate a branded UUID type for type-safe ID handling.

        Args:
            brand_name: Brand name (e.g., 'AgentId', 'RunId').

        Returns:
            TypeScript source string for the branded UUID type.
        """
        return (
            f"/** Branded UUID type for {brand_name} identifiers. */\n"
            f"export type {brand_name} = string & {{ readonly __brand: '{brand_name}' }};\n"
        )

    def generate_resource_class(
        self,
        resource_name: str,
        operations: list[dict[str, Any]],
    ) -> str:
        """Generate a TypeScript resource class for a group of API operations.

        Args:
            resource_name: Class name (e.g., 'AgentsResource').
            operations: List of operation dicts.

        Returns:
            TypeScript source string for the resource class.
        """
        lines: list[str] = [
            f"/** Resource class for {resource_name.replace('Resource', '').lower()} operations. */",
            f"export class {resource_name} {{",
            "  constructor(private readonly client: AumOSHTTPClient) {}",
            "",
        ]

        for operation in operations:
            method_source = self._generate_operation_method(operation)
            lines.append(method_source)

        lines.append("}")
        return "\n".join(lines)

    def generate_error_classes(self) -> str:
        """Generate the TypeScript error class hierarchy for the SDK.

        Returns:
            TypeScript source string with all error class definitions.
        """
        return """\
/** Base error class for all AumOS SDK errors. */
export class AumOSError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AumOSError";
  }
}

/** Error raised for AumOS API HTTP error responses. */
export class AumOSAPIError extends AumOSError {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly errorCode: string | null = null,
    public readonly requestId: string | null = null,
  ) {
    super(message);
    this.name = "AumOSAPIError";
  }
}

/** Raised when authentication credentials are missing or invalid. */
export class AuthenticationError extends AumOSAPIError {
  constructor(message: string, requestId?: string) {
    super(message, 401, "AUTH_ERROR", requestId ?? null);
    this.name = "AuthenticationError";
  }
}

/** Raised when the caller lacks permission for the requested resource. */
export class PermissionError extends AumOSAPIError {
  constructor(message: string, requestId?: string) {
    super(message, 403, "PERMISSION_ERROR", requestId ?? null);
    this.name = "PermissionError";
  }
}

/** Raised when a requested resource is not found. */
export class NotFoundError extends AumOSAPIError {
  constructor(message: string, requestId?: string) {
    super(message, 404, "NOT_FOUND", requestId ?? null);
    this.name = "NotFoundError";
  }
}

/** Raised when request validation fails. */
export class ValidationError extends AumOSAPIError {
  constructor(message: string, requestId?: string) {
    super(message, 422, "VALIDATION_ERROR", requestId ?? null);
    this.name = "ValidationError";
  }
}

/** Raised when the API rate limit is exceeded. */
export class RateLimitError extends AumOSAPIError {
  constructor(message: string, public readonly retryAfterSeconds: number = 60) {
    super(message, 429, "RATE_LIMITED");
    this.name = "RateLimitError";
  }
}

/** Raised for 5xx server-side errors. */
export class ServerError extends AumOSAPIError {
  constructor(message: string, statusCode: number, requestId?: string) {
    super(message, statusCode, "SERVER_ERROR", requestId ?? null);
    this.name = "ServerError";
  }
}
"""

    def generate_http_client_class(self) -> str:
        """Generate the base TypeScript HTTP client used by all resource classes.

        Returns:
            TypeScript source string for the AumOSHTTPClient class.
        """
        return f'''\
/** Base HTTP client for AumOS SDK resource classes. */
export class AumOSHTTPClient {{
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;

  constructor(options: {{ apiKey?: string; baseUrl?: string; bearerToken?: string }}) {{
    this.baseUrl = options.baseUrl ?? "{self._api_base_url}";
    const authHeader = options.apiKey
      ? `Bearer ${{options.apiKey}}`
      : options.bearerToken
        ? `Bearer ${{options.bearerToken}}`
        : "";
    this.headers = {{
      "Content-Type": "application/json",
      "Accept": "application/json",
      ...(authHeader ? {{ Authorization: authHeader }} : {{}}),
    }};
  }}

  async request<T>(
    method: string,
    path: string,
    options?: {{
      params?: Record<string, string | number | boolean>;
      body?: unknown;
    }},
  ): Promise<T> {{
    const url = new URL(path, this.baseUrl);
    if (options?.params) {{
      for (const [key, value] of Object.entries(options.params)) {{
        url.searchParams.set(key, String(value));
      }}
    }}
    const response = await fetch(url.toString(), {{
      method,
      headers: this.headers,
      body: options?.body != null ? JSON.stringify(options.body) : undefined,
    }});
    if (!response.ok) {{
      const body = await response.json().catch(() => ({{}}));
      this.throwForStatus(response.status, body as Record<string, unknown>);
    }}
    return response.json() as Promise<T>;
  }}

  private throwForStatus(status: number, body: Record<string, unknown>): never {{
    const message = (body["message"] as string) ?? `HTTP ${{status}} error`;
    const requestId = (body["request_id"] as string | undefined) ?? undefined;
    if (status === 401) throw new AuthenticationError(message, requestId);
    if (status === 403) throw new PermissionError(message, requestId);
    if (status === 404) throw new NotFoundError(message, requestId);
    if (status === 422) throw new ValidationError(message, requestId);
    if (status === 429) throw new RateLimitError(message);
    if (status >= 500) throw new ServerError(message, status, requestId);
    throw new AumOSAPIError(message, status);
  }}
}}
'''

    def generate_barrel_export(self, exported_names: list[str]) -> str:
        """Generate a TypeScript barrel export (index.ts) for listed names.

        Args:
            exported_names: List of names to re-export (modules or classes).

        Returns:
            TypeScript source string for the index barrel file.
        """
        lines: list[str] = [
            '/**',
            ' * AumOS TypeScript SDK — generated barrel export.',
            ' * DO NOT EDIT — regenerate via: make generate-typescript',
            ' */',
            "",
        ]
        for name in sorted(exported_names):
            lines.append(f'export {{ {name} }} from "./{name}";')
        return "\n".join(lines)

    def generate_all_types(self, spec: dict[str, Any]) -> str:
        """Generate all TypeScript interfaces from the OpenAPI spec's component schemas.

        Args:
            spec: OpenAPI spec dict with components.schemas.

        Returns:
            TypeScript source string with all interface definitions.
        """
        schemas = spec.get("components", {}).get("schemas", {})
        lines: list[str] = [
            _TS_HEADER,
            "",
            "// ============================================================",
            "// AumOS API Types",
            "// ============================================================",
            "",
        ]

        for schema_name in sorted(schemas):
            interface_source = self.generate_interface(schema_name, schemas[schema_name])
            lines.extend([interface_source, ""])

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_type(self, schema: dict[str, Any]) -> str:
        """Resolve an OpenAPI property schema to a TypeScript type string.

        Args:
            schema: OpenAPI property schema dict.

        Returns:
            TypeScript type string.
        """
        ref = schema.get("$ref", "")
        if ref:
            return ref.split("/")[-1]

        schema_format = schema.get("format", "")
        if schema_format in _FORMAT_OVERRIDES:
            return _FORMAT_OVERRIDES[schema_format]

        schema_type = schema.get("type", "object")
        if schema_type == "array":
            item_schema = schema.get("items", {})
            item_type = self._resolve_type(item_schema)
            return f"ReadonlyArray<{item_type}>"

        enum_values = schema.get("enum")
        if enum_values:
            return " | ".join(f'"{v}"' for v in enum_values)

        nullable = schema.get("nullable", False)
        ts_type = _OPENAPI_TO_TYPESCRIPT_TYPES.get(schema_type, "unknown")
        return f"{ts_type} | null" if nullable else ts_type

    def _generate_operation_method(self, operation: dict[str, Any]) -> str:
        """Generate a TypeScript async method for a single API operation.

        Args:
            operation: Operation dict from the codegen.

        Returns:
            TypeScript source string for the async method.
        """
        method_name = self._derive_method_name(operation)
        http_method = operation.get("method", "GET")
        path = operation.get("path", "/")
        summary = operation.get("summary", f"Call {http_method} {path}.")
        has_body = operation.get("has_request_body", False)

        params: list[str] = []
        import re
        path_params = re.findall(r"\{(\w+)\}", path)
        for param in path_params:
            params.append(f"{param}: string")

        if has_body:
            params.append("body: Record<string, unknown>")

        params_str = ", ".join(params)

        ts_path = path
        for param in path_params:
            ts_path = ts_path.replace(f"{{{param}}}", f"${{{param}}}")

        body_arg = ", { body }" if has_body else ""

        return (
            f"  /** {summary} */\n"
            f"  async {method_name}({params_str}): Promise<Record<string, unknown>> {{\n"
            f"    return this.client.request<Record<string, unknown>>(\"{http_method}\", `{ts_path}`{body_arg});\n"
            f"  }}\n"
        )

    def _derive_method_name(self, operation: dict[str, Any]) -> str:
        """Derive a camelCase TypeScript method name from an operation.

        Args:
            operation: Operation dict.

        Returns:
            camelCase method name string.
        """
        operation_id = operation.get("operation_id", "")
        if operation_id:
            return self._to_camel_case(operation_id)

        method = operation.get("method", "GET").lower()
        path = operation.get("path", "").strip("/").split("/")[-1]
        return f"{method}{path.capitalize()}"

    def _to_camel_case(self, name: str) -> str:
        """Convert a snake_case or PascalCase name to camelCase.

        Args:
            name: Input identifier string.

        Returns:
            camelCase identifier.
        """
        parts = name.replace("-", "_").split("_")
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])
