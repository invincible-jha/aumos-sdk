"""OpenTelemetry tracing integration for the AumOS Python SDK.

Creates client-side spans for every API call with standard HTTP and AumOS-specific
attributes. Propagates W3C traceparent headers to the server.

When no OTEL exporter is configured, this module has zero performance impact
because OpenTelemetry uses a noop tracer by default.

Usage:
    The tracing module is used internally by the SDK's HTTP layer.
    Users configure their own OTEL exporters (Jaeger, Grafana Tempo, etc.)
    and spans appear automatically.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, Span, SpanKind, use_span
from opentelemetry.propagators.textmap import DefaultGetter, DefaultSetter
from opentelemetry.propagate import inject

_TRACER_NAME = "aumos-sdk"
_SCHEMA_URL = "https://opentelemetry.io/schemas/1.23.0"

_tracer = trace.get_tracer(_TRACER_NAME, schema_url=_SCHEMA_URL)


@contextmanager
def api_span(
    resource: str,
    operation: str,
    url: str,
    http_method: str = "GET",
) -> Generator[Span, None, None]:
    """Context manager that creates an OpenTelemetry span for an AumOS API call.

    Sets standard HTTP semantic convention attributes plus AumOS-specific attributes.
    The span is automatically ended when the context exits.

    Args:
        resource: The AumOS resource type (e.g., 'agents', 'data', 'governance').
        operation: The operation being performed (e.g., 'create', 'list', 'generate').
        url: The full API URL being called.
        http_method: The HTTP method (GET, POST, PATCH, DELETE).

    Yields:
        The active Span for adding custom attributes or events.
    """
    with _tracer.start_as_current_span(
        name=f"aumos.{resource}.{operation}",
        kind=SpanKind.CLIENT,
        attributes={
            "aumos.resource": resource,
            "aumos.operation": operation,
            "http.url": url,
            "http.method": http_method.upper(),
        },
    ) as span:
        yield span


def inject_trace_headers(headers: dict[str, str]) -> dict[str, str]:
    """Inject W3C traceparent/tracestate headers into the given headers dict.

    Enables distributed tracing from SDK call through API gateway to downstream services.

    Args:
        headers: Existing HTTP headers dict to inject into.

    Returns:
        The same headers dict with traceparent and tracestate added if a span is active.
    """
    inject(headers)
    return headers


def record_http_response(span: Span, status_code: int) -> None:
    """Record the HTTP response status code on the active span.

    Args:
        span: The active span created by api_span().
        status_code: The HTTP response status code.
    """
    if isinstance(span, NonRecordingSpan):
        return
    span.set_attribute("http.status_code", status_code)
    if status_code >= 400:
        span.set_status(trace.Status(trace.StatusCode.ERROR, f"HTTP {status_code}"))
