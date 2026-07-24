"""Environment-driven configuration for the Product MCP Server."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _read_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero, got {value}.")
    return value


def _read_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero, got {value}.")
    return value


def _read_optional_database_url() -> str | None:
    """Read DATABASE_URL without logging or returning credentials elsewhere."""

    raw = os.environ.get("DATABASE_URL")
    if raw is None:
        return None
    value = raw.strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the Product MCP Server."""

    product_api_url: str
    product_api_timeout: float
    mcp_host: str
    mcp_port: int
    mcp_transport: str
    log_level: str
    database_url: str | None

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from environment variables.

        PRODUCT_API_URL defaults to the host-published Product API port used by
        this monorepo's Docker Compose foundation.

        DATABASE_URL is required at process startup when stock tools are
        enabled (the default). Product tools still use PRODUCT_API_URL only.
        """

        product_api_url = os.environ.get(
            "PRODUCT_API_URL",
            "http://localhost:5001",
        ).rstrip("/")
        if not product_api_url:
            raise ValueError("PRODUCT_API_URL must not be empty.")

        transport = os.environ.get("MCP_TRANSPORT", "streamable-http").strip()
        if transport not in {"streamable-http", "stdio"}:
            raise ValueError(
                "MCP_TRANSPORT must be 'streamable-http' or 'stdio', "
                f"got {transport!r}."
            )

        return cls(
            product_api_url=product_api_url,
            product_api_timeout=_read_float("PRODUCT_API_TIMEOUT", 5.0),
            mcp_host=os.environ.get("MCP_HOST", "127.0.0.1"),
            mcp_port=_read_int("MCP_PORT", 8001),
            mcp_transport=transport,
            log_level=os.environ.get("MCP_LOG_LEVEL", "INFO").upper(),
            database_url=_read_optional_database_url(),
        )
