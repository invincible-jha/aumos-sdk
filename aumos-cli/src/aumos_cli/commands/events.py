"""AumOS CLI events command group.

Provides:
    aumos events listen   — forward Kafka events to a local webhook URL
    aumos events trigger  — send a synthetic test event to the platform
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Optional

import click
import httpx

try:
    from confluent_kafka import Consumer, KafkaException
    _KAFKA_AVAILABLE = True
except ImportError:
    _KAFKA_AVAILABLE = False


def _get_bootstrap_servers() -> str:
    """Read Kafka bootstrap servers from environment.

    Returns:
        Comma-separated list of broker addresses.

    Raises:
        click.ClickException: If AUMOS_KAFKA_BOOTSTRAP_SERVERS is not set.
    """
    servers = os.environ.get("AUMOS_KAFKA_BOOTSTRAP_SERVERS", "")
    if not servers:
        raise click.ClickException(
            "AUMOS_KAFKA_BOOTSTRAP_SERVERS environment variable is required. "
            "Example: export AUMOS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092"
        )
    return servers


def _random_group_id() -> str:
    """Generate a unique Kafka consumer group ID for this CLI session."""
    return f"aumos-cli-{uuid.uuid4().hex[:8]}"


@click.group()
def events() -> None:
    """Manage AumOS event subscriptions for local development."""


@events.command()
@click.option(
    "--topics",
    "-t",
    multiple=True,
    help="Kafka topic patterns to listen on (default: aumos.#)",
)
@click.option(
    "--forward-to",
    "-f",
    required=True,
    help="Local webhook URL to forward events to (e.g., http://localhost:3001/webhook)",
)
@click.option(
    "--filter",
    "event_filter",
    default=None,
    help="Filter events by type (e.g., 'agent.run.completed')",
)
def listen(
    topics: tuple[str, ...],
    forward_to: str,
    event_filter: Optional[str],
) -> None:
    """Forward AumOS platform events to a local webhook URL.

    This mirrors the Stripe CLI's `stripe listen` command for local development.
    Events appear at your local endpoint within 500ms of being published.

    Example:
        aumos events listen --topics aumos.agent.# --forward-to http://localhost:3001/webhook

        aumos events listen --forward-to http://localhost:3001/webhook \\
            --filter agent.run.completed
    """
    if not _KAFKA_AVAILABLE:
        raise click.ClickException(
            "confluent-kafka is required for event listening. "
            "Install with: pip install confluent-kafka"
        )

    effective_topics = list(topics) if topics else ["aumos.#"]
    click.echo(f"Listening for events on: {', '.join(effective_topics)}")
    click.echo(f"Forwarding to: {forward_to}")
    if event_filter:
        click.echo(f"Filter: {event_filter}")
    click.echo("Press Ctrl+C to stop.\n")

    try:
        asyncio.run(_run_listener(effective_topics, forward_to, event_filter))
    except KeyboardInterrupt:
        click.echo("\nStopped.")


async def _run_listener(
    topics: list[str],
    forward_to: str,
    event_filter: Optional[str],
) -> None:
    """Async implementation of the event listener."""
    consumer = Consumer({
        "bootstrap.servers": _get_bootstrap_servers(),
        "group.id": _random_group_id(),
        "auto.offset.reset": "latest",
        "enable.auto.commit": True,
    })
    consumer.subscribe(topics)

    async with httpx.AsyncClient(timeout=10.0) as http:
        while True:
            msg = consumer.poll(timeout=0.1)
            if msg is None:
                await asyncio.sleep(0.05)
                continue
            if msg.error():
                click.echo(f"ERROR: {msg.error()}", err=True)
                continue

            try:
                event = json.loads(msg.value())
            except json.JSONDecodeError:
                click.echo(f"WARN: Non-JSON message on {msg.topic()}", err=True)
                continue

            event_type = event.get("type", "unknown")
            if event_filter and event_type != event_filter:
                continue

            click.echo(f"--> {event_type} [{msg.topic()}]")
            try:
                response = await http.post(forward_to, json=event)
                status_color = "green" if response.status_code < 300 else "red"
                click.echo(f"<-- {response.status_code}")
            except httpx.ConnectError:
                click.echo(f"ERROR: Cannot reach {forward_to} — is your local server running?", err=True)


@events.command()
@click.argument("event_type")
@click.option(
    "--data",
    "event_data",
    default="{}",
    help="JSON payload to include in the event (default: {})",
)
def trigger(event_type: str, event_data: str) -> None:
    """Send a synthetic test event to the AumOS event bus.

    Useful for testing event consumers without waiting for real platform events.

    Example:
        aumos events trigger agent.run.completed
        aumos events trigger agent.run.completed --data '{"agent_id": "abc-123"}'
    """
    try:
        payload = json.loads(event_data)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in --data: {exc}") from exc

    api_key = os.environ.get("AUMOS_API_KEY", "")
    if not api_key:
        raise click.ClickException("AUMOS_API_KEY environment variable is required.")

    base_url = os.environ.get("AUMOS_BASE_URL", "https://api.aumos.ai")

    async def _trigger() -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{base_url}/api/v1/events/test",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"type": event_type, "data": payload},
            )
            response.raise_for_status()
            click.echo(f"Triggered: {event_type}")
            click.echo(response.json())

    try:
        asyncio.run(_trigger())
    except httpx.HTTPStatusError as exc:
        raise click.ClickException(f"API error: {exc.response.status_code} {exc.response.text}") from exc
