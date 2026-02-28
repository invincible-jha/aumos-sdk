"""AumOS CLI entry point.

Commands:
    aumos events listen  — forward Kafka events to a local webhook (like Stripe CLI)
    aumos events trigger — send a synthetic test event
    aumos api get/post   — raw API calls with auth
    aumos config set/get — credential management
"""

from __future__ import annotations

import click

from aumos_cli.commands.events import events
from aumos_cli.commands.api import api
from aumos_cli.commands.config import config


@click.group()
@click.version_option(package_name="aumos-cli")
def cli() -> None:
    """AumOS CLI — developer tooling for local AumOS integration.

    Mirrors the Stripe CLI pattern: forward events, test API calls,
    and manage credentials without leaving the terminal.

    Quick start:
        aumos config set api-key your-api-key
        aumos events listen --forward-to http://localhost:3001/webhook
    """


cli.add_command(events)
cli.add_command(api)
cli.add_command(config)

if __name__ == "__main__":
    cli()
