"""Configuration for the AumOS MCP server.

All settings are loaded from environment variables with the AUMOS_ prefix.
"""

from __future__ import annotations

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerConfig(BaseSettings):
    """AumOS MCP server configuration.

    All values are sourced from environment variables. The server will not start
    if AUMOS_API_KEY is not set.
    """

    model_config = SettingsConfigDict(env_prefix="AUMOS_", env_file=".env", extra="ignore")

    api_key: str = Field(..., description="AumOS API key for authenticating SDK calls")
    aumos_base_url: AnyHttpUrl = Field(
        default="https://api.aumos.ai",  # type: ignore[assignment]
        description="Base URL for the AumOS API",
    )
    log_level: str = Field(default="INFO", description="Log level for the MCP server")
    max_retries: int = Field(default=3, description="Maximum SDK retry attempts")
