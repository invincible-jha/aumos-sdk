"""AumOS CLI api command group.

Provides raw authenticated API calls for debugging and exploration:
    aumos api get /api/v1/agents
    aumos api post /api/v1/agents --data '{"name": "my-agent", ...}'
"""

from __future__ import annotations

import asyncio
import json
import os

import click
import httpx


def _get_api_key() -> str:
    """Read the API key from the environment.

    Returns:
        The API key string.

    Raises:
        click.ClickException: If AUMOS_API_KEY is not set.
    """
    api_key = os.environ.get("AUMOS_API_KEY", "")
    if not api_key:
        raise click.ClickException(
            "AUMOS_API_KEY is not set. Run: aumos config set api-key your-key"
        )
    return api_key


def _get_base_url() -> str:
    """Read the base URL from environment with a sensible default."""
    return os.environ.get("AUMOS_BASE_URL", "https://api.aumos.ai")


@click.group()
def api() -> None:
    """Make raw authenticated API calls to the AumOS platform."""


@api.command(name="get")
@click.argument("path")
@click.option("--header", "-H", multiple=True, help="Additional headers in Key: Value format")
def api_get(path: str, header: tuple[str, ...]) -> None:
    """Execute a GET request to an AumOS API endpoint.

    PATH is the API path (e.g., /api/v1/agents).

    Example:
        aumos api get /api/v1/agents
        aumos api get /api/v1/agents/abc-123
    """
    asyncio.run(_make_request("GET", path, extra_headers=header))


@api.command(name="post")
@click.argument("path")
@click.option("--data", "-d", default="{}", help="JSON request body")
@click.option("--header", "-H", multiple=True, help="Additional headers in Key: Value format")
def api_post(path: str, data: str, header: tuple[str, ...]) -> None:
    """Execute a POST request to an AumOS API endpoint.

    PATH is the API path. Use --data to provide a JSON body.

    Example:
        aumos api post /api/v1/agents --data '{"name": "my-agent", "model": "claude-opus-4-6"}'
    """
    try:
        body = json.loads(data)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in --data: {exc}") from exc

    asyncio.run(_make_request("POST", path, json_body=body, extra_headers=header))


async def _make_request(
    method: str,
    path: str,
    json_body: dict | None = None,
    extra_headers: tuple[str, ...] = (),
) -> None:
    """Shared implementation for authenticated API requests."""
    api_key = _get_api_key()
    base_url = _get_base_url()

    full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for header_line in extra_headers:
        if ":" in header_line:
            key, value = header_line.split(":", 1)
            headers[key.strip()] = value.strip()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method=method,
                url=full_url,
                headers=headers,
                json=json_body,
            )
            click.echo(f"HTTP {response.status_code}")
            try:
                parsed = response.json()
                click.echo(json.dumps(parsed, indent=2))
            except json.JSONDecodeError:
                click.echo(response.text)
        except httpx.ConnectError as exc:
            raise click.ClickException(f"Cannot connect to {base_url}: {exc}") from exc
