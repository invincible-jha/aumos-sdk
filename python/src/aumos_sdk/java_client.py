"""Java SDK client generator for the AumOS SDK.

Generates idiomatic Java client code from an OpenAPI specification for the AumOS
Java SDK's `_generated/` layer. Produces Java 17+ POJO classes with Gson annotations,
sealed exception hierarchy, OkHttp-based service classes, and builder patterns.
"""

import re
from typing import Any

# OpenAPI type → Java type mappings
_OPENAPI_TO_JAVA_TYPES: dict[str, str] = {
    "string": "String",
    "integer": "long",
    "number": "double",
    "boolean": "boolean",
    "array": "List",
    "object": "Map<String, Object>",
}

# Java format-specific overrides
_FORMAT_TO_JAVA: dict[str, str] = {
    "uuid": "String",
    "date-time": "String",  # ISO 8601
    "date": "String",
    "int32": "int",
    "int64": "long",
    "float": "float",
    "double": "double",
    "email": "String",
    "uri": "String",
    "binary": "byte[]",
}

# Java file preamble
_JAVA_PACKAGE: str = "io.aumos.sdk.generated"

# Boxed type lookup for optional fields
_JAVA_BOXED_TYPES: dict[str, str] = {
    "int": "Integer",
    "long": "Long",
    "double": "Double",
    "float": "Float",
    "boolean": "Boolean",
}


class JavaClientGenerator:
    """Generates Java SDK client code from an OpenAPI specification.

    Produces Java 17+ POJO classes (with Gson @SerializedName annotations),
    a sealed exception hierarchy, OkHttp-based service classes, and builder
    patterns for all request types. Output is formatted for the AumOS Java SDK
    `_generated/` directory and should not be imported directly by user code.
    """

    def __init__(
        self,
        package_name: str = _JAVA_PACKAGE,
        api_base_url: str = "https://api.aumos.ai",
    ) -> None:
        """Initialise the Java client generator.

        Args:
            package_name: Java package name for generated classes.
            api_base_url: Default base URL for the generated client.
        """
        self._package_name = package_name
        self._api_base_url = api_base_url

    def generate_pojo(
        self,
        class_name: str,
        schema: dict[str, Any],
    ) -> str:
        """Generate a Java POJO class from an OpenAPI schema.

        Args:
            class_name: Java class name (PascalCase).
            schema: OpenAPI JSON schema dict.

        Returns:
            Java source string for the POJO class with Gson annotations.
        """
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))
        description = schema.get("description", f"AumOS {class_name} model.")

        lines: list[str] = [
            f"package {self._package_name};",
            "",
            "import com.google.gson.annotations.SerializedName;",
            "import java.util.List;",
            "import java.util.Map;",
            "import java.util.Objects;",
            "",
            f"/** {description} */",
            f"public final class {class_name} {{",
            "",
        ]

        field_names: list[str] = []
        java_types: list[str] = []

        for prop_name, prop_schema in properties.items():
            java_type = self._resolve_type(prop_schema, required_fields, prop_name)
            field_name = self._to_camel_case(prop_name)
            field_names.append(field_name)
            java_types.append(java_type)

            prop_description = prop_schema.get("description", "")
            if prop_description:
                lines.append(f"    /** {prop_description} */")
            if prop_name != field_name:
                lines.append(f'    @SerializedName("{prop_name}")')
            lines.append(f"    private final {java_type} {field_name};")
            lines.append("")

        # Private all-args constructor
        constructor_params = ", ".join(
            f"{java_type} {name}" for java_type, name in zip(java_types, field_names)
        )
        lines.extend([
            f"    private {class_name}({constructor_params}) {{",
        ])
        for name in field_names:
            lines.append(f"        this.{name} = {name};")
        lines.extend(["    }", ""])

        # Getters
        for java_type, field_name in zip(java_types, field_names):
            getter_name = "is" + field_name.capitalize() if java_type == "boolean" else "get" + field_name.capitalize()
            lines.extend([
                f"    /** Returns the {field_name}. */",
                f"    public {java_type} {getter_name}() {{",
                f"        return {field_name};",
                "    }",
                "",
            ])

        # Builder inner class
        lines.extend(self._generate_builder(class_name, field_names, java_types))
        lines.extend([
            "    /** Returns a new builder for this class. */",
            f"    public static Builder builder() {{ return new Builder(); }}",
            "",
            "}",
        ])

        return "\n".join(lines)

    def generate_exception_hierarchy(self) -> str:
        """Generate the Java sealed exception hierarchy for the SDK.

        Returns:
            Java source string with all exception class definitions.
        """
        return f'''\
package {self._package_name};

/**
 * Base exception for all AumOS SDK errors.
 * Use try-catch on AumOSException to handle all SDK failures.
 */
public sealed class AumOSException extends RuntimeException
    permits AumOSAPIException, AumOSConnectionException, AumOSTimeoutException {{

    public AumOSException(String message) {{ super(message); }}
    public AumOSException(String message, Throwable cause) {{ super(message, cause); }}
}}

/** Exception raised for AumOS API HTTP error responses (4xx, 5xx). */
public final class AumOSAPIException extends AumOSException {{
    private final int statusCode;
    private final String errorCode;
    private final String requestId;

    public AumOSAPIException(String message, int statusCode, String errorCode, String requestId) {{
        super(message);
        this.statusCode = statusCode;
        this.errorCode = errorCode;
        this.requestId = requestId;
    }}

    public int getStatusCode() {{ return statusCode; }}
    public String getErrorCode() {{ return errorCode; }}
    public String getRequestId() {{ return requestId; }}

    public boolean isRetryable() {{
        return statusCode == 429 || (statusCode >= 500 && statusCode < 600);
    }}

    @Override
    public String toString() {{
        return String.format("AumOSAPIException[%d]: %s (errorCode=%s, requestId=%s)",
            statusCode, getMessage(), errorCode, requestId);
    }}
}}

/** Exception raised when a network connection to the AumOS API fails. */
public final class AumOSConnectionException extends AumOSException {{
    public AumOSConnectionException(String message, Throwable cause) {{ super(message, cause); }}
}}

/** Exception raised when an AumOS API request times out. */
public final class AumOSTimeoutException extends AumOSException {{
    public AumOSTimeoutException(String message) {{ super(message); }}
}}
'''

    def generate_client_class(self) -> str:
        """Generate the root Java AumOSClient class with OkHttp and builder pattern.

        Returns:
            Java source string for the AumOSClient class.
        """
        return f'''\
package {self._package_name};

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import okhttp3.*;
import java.io.IOException;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

/**
 * Root client for the AumOS API. Use {{@link Builder}} to construct.
 *
 * <pre>{{@code
 * try (AumOSClient client = AumOSClient.builder().apiKey("your-key").build()) {{
 *     AgentPage agents = client.agents().list(20, 1);
 * }}
 * }}</pre>
 */
public final class AumOSClient implements AutoCloseable {{

    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    private final String baseUrl;
    private final String apiKey;
    private final OkHttpClient httpClient;
    private final Gson gson;

    private AumOSClient(Builder builder) {{
        this.baseUrl = Objects.requireNonNull(builder.baseUrl, "baseUrl");
        this.apiKey = builder.apiKey;
        this.httpClient = new OkHttpClient.Builder()
            .connectTimeout(builder.connectTimeoutSeconds, TimeUnit.SECONDS)
            .readTimeout(builder.readTimeoutSeconds, TimeUnit.SECONDS)
            .build();
        this.gson = new GsonBuilder().create();
    }}

    /** Execute a JSON request and deserialize the response. */
    public <T> T request(String method, String path, Object requestBody, Class<T> responseType)
            throws AumOSException {{
        String url = baseUrl + path;
        RequestBody body = requestBody != null
            ? RequestBody.create(gson.toJson(requestBody), JSON)
            : null;

        Request request = new Request.Builder()
            .url(url)
            .header("Authorization", "Bearer " + apiKey)
            .header("Accept", "application/json")
            .method(method, body)
            .build();

        try (Response response = httpClient.newCall(request).execute()) {{
            String responseBodyStr = response.body() != null ? response.body().string() : "";
            if (!response.isSuccessful()) {{
                throw parseError(response.code(), responseBodyStr);
            }}
            return gson.fromJson(responseBodyStr, responseType);
        }} catch (IOException e) {{
            throw new AumOSConnectionException("Connection failed: " + e.getMessage(), e);
        }}
    }}

    private AumOSAPIException parseError(int status, String body) {{
        try {{
            var errBody = gson.fromJson(body, java.util.Map.class);
            String message = (String) errBody.getOrDefault("message", "Unknown error");
            String errorCode = (String) errBody.getOrDefault("error_code", "");
            String requestId = (String) errBody.getOrDefault("request_id", "");
            return new AumOSAPIException(message, status, errorCode, requestId);
        }} catch (Exception e) {{
            return new AumOSAPIException("HTTP " + status, status, "", "");
        }}
    }}

    @Override
    public void close() {{
        httpClient.dispatcher().executorService().shutdown();
        httpClient.connectionPool().evictAll();
    }}

    /** Builder for constructing an {{@link AumOSClient}}. */
    public static final class Builder {{
        private String baseUrl = "{self._api_base_url}";
        private String apiKey;
        private long connectTimeoutSeconds = 10L;
        private long readTimeoutSeconds = 30L;

        /** Set the API key for Bearer token authentication. */
        public Builder apiKey(String key) {{ this.apiKey = key; return this; }}

        /** Override the default API base URL. */
        public Builder baseUrl(String url) {{ this.baseUrl = url; return this; }}

        /** Set the connection timeout in seconds. */
        public Builder connectTimeout(long seconds) {{ this.connectTimeoutSeconds = seconds; return this; }}

        /** Set the read timeout in seconds. */
        public Builder readTimeout(long seconds) {{ this.readTimeoutSeconds = seconds; return this; }}

        /** Build the {{@link AumOSClient}} instance. */
        public AumOSClient build() {{
            Objects.requireNonNull(apiKey, "apiKey must be set");
            return new AumOSClient(this);
        }}
    }}

    /** Factory method: returns a new builder. */
    public static Builder builder() {{ return new Builder(); }}
}}
'''

    def generate_all_pojos(self, spec: dict[str, Any]) -> list[dict[str, str]]:
        """Generate all Java POJO classes from an OpenAPI spec's component schemas.

        Args:
            spec: OpenAPI spec dict with components.schemas.

        Returns:
            List of dicts with class_name and java_source for each schema.
        """
        schemas = spec.get("components", {}).get("schemas", {})
        results: list[dict[str, str]] = []

        for schema_name in sorted(schemas):
            java_source = self.generate_pojo(schema_name, schemas[schema_name])
            results.append({
                "class_name": schema_name,
                "file_name": f"{schema_name}.java",
                "java_source": java_source,
                "package": self._package_name,
            })

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_type(
        self,
        schema: dict[str, Any],
        required_fields: set[str],
        prop_name: str,
    ) -> str:
        """Resolve an OpenAPI property schema to a Java type string.

        Args:
            schema: OpenAPI property schema dict.
            required_fields: Set of required field names.
            prop_name: Property name for required check.

        Returns:
            Java type string (boxed for optional primitives).
        """
        ref = schema.get("$ref", "")
        if ref:
            return ref.split("/")[-1]

        schema_format = schema.get("format", "")
        if schema_format in _FORMAT_TO_JAVA:
            java_type = _FORMAT_TO_JAVA[schema_format]
        else:
            schema_type = schema.get("type", "object")
            if schema_type == "array":
                item_schema = schema.get("items", {})
                item_type = self._resolve_type(item_schema, set(), "")
                return f"List<{item_type}>"
            java_type = _OPENAPI_TO_JAVA_TYPES.get(schema_type, "Object")

        # Box primitives for optional fields
        if prop_name not in required_fields and java_type in _JAVA_BOXED_TYPES:
            return _JAVA_BOXED_TYPES[java_type]

        return java_type

    def _to_camel_case(self, name: str) -> str:
        """Convert a snake_case name to camelCase for Java field names.

        Args:
            name: Input identifier (snake_case or camelCase).

        Returns:
            camelCase identifier.
        """
        parts = re.split(r"[_\-]", name)
        if not parts:
            return name
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

    def _generate_builder(
        self,
        class_name: str,
        field_names: list[str],
        java_types: list[str],
    ) -> list[str]:
        """Generate a Builder inner class for a Java POJO.

        Args:
            class_name: Outer class name.
            field_names: List of field name strings.
            java_types: List of Java type strings corresponding to field_names.

        Returns:
            List of Java source lines for the Builder inner class.
        """
        lines: list[str] = [
            f"    /** Builder for {{@link {class_name}}}. */",
            f"    public static final class Builder {{",
        ]
        for java_type, field_name in zip(java_types, field_names):
            lines.append(f"        private {java_type} {field_name};")
        lines.append("")

        for java_type, field_name in zip(java_types, field_names):
            setter_name = field_name
            lines.extend([
                f"        public Builder {setter_name}({java_type} value) {{",
                f"            this.{field_name} = value;",
                f"            return this;",
                f"        }}",
                "",
            ])

        constructor_args = ", ".join(field_names)
        lines.extend([
            f"        public {class_name} build() {{",
            f"            return new {class_name}({constructor_args});",
            f"        }}",
            "    }",
            "",
        ])
        return lines
