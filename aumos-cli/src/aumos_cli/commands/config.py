"""AumOS CLI config command group.

Manages AumOS credentials and configuration for local development:
    aumos config set api-key your-api-key
    aumos config get api-key
    aumos config list
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

_CONFIG_DIR = Path.home() / ".aumos"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


def _load_config() -> dict[str, str]:
    """Load the config file, returning an empty dict if it does not exist."""
    if not _CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_config(data: dict[str, str]) -> None:
    """Persist the config dict to the config file."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _CONFIG_FILE.chmod(0o600)  # owner-read-write only for security


@click.group()
def config() -> None:
    """Manage AumOS credentials and configuration."""


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value.

    Common keys:
        api-key        AumOS API key
        base-url       AumOS API base URL (default: https://api.aumos.ai)
        kafka-brokers  Kafka bootstrap servers for event listening

    Example:
        aumos config set api-key sk-aumos-xxxxx
        aumos config set base-url https://sandbox.aumos.ai
    """
    data = _load_config()
    data[key] = value
    _save_config(data)
    click.echo(f"Set {key} = {'*' * len(value) if 'key' in key.lower() else value}")


@config.command(name="get")
@click.argument("key")
def config_get(key: str) -> None:
    """Get a configuration value.

    Example:
        aumos config get api-key
        aumos config get base-url
    """
    data = _load_config()
    if key not in data:
        raise click.ClickException(f"Config key '{key}' not found. Use: aumos config set {key} <value>")
    value = data[key]
    if "key" in key.lower():
        click.echo(f"{key} = {'*' * len(value)}")
    else:
        click.echo(f"{key} = {value}")


@config.command(name="list")
def config_list() -> None:
    """List all configuration values.

    API keys are masked for security.
    """
    data = _load_config()
    if not data:
        click.echo("No configuration set. Use: aumos config set api-key your-api-key")
        return
    for key, value in data.items():
        display_value = "*" * len(value) if "key" in key.lower() else value
        click.echo(f"{key} = {display_value}")
