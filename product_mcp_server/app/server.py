"""Product MCP Server entry point.

Exposes read-only product tools over MCP Streamable HTTP (default) or stdio.
Stock tools, AI agents, and PostgreSQL access are intentionally out of scope.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from product_mcp_server.app.config import Settings
from product_mcp_server.app.product_api_client import ProductApiClient
from product_mcp_server.app.tools import SupportsProductApi, register_product_tools

logger = logging.getLogger(__name__)

SERVER_INSTRUCTIONS = (
    "HBntory Product MCP Server. Read-only tools for the official External "
    "Product API catalog. Does not store product data, does not modify stock, "
    "and has no direct database access. Use list_products and "
    "get_product_details only."
)


def create_mcp_server(
    settings: Settings,
    *,
    client: Optional[SupportsProductApi] = None,
) -> tuple[FastMCP, SupportsProductApi]:
    """Build a configured FastMCP server with product tools registered."""

    product_client: SupportsProductApi = client or ProductApiClient(
        base_url=settings.product_api_url,
        timeout=settings.product_api_timeout,
    )

    mcp = FastMCP(
        name="hbntory-product-mcp",
        instructions=SERVER_INSTRUCTIONS,
        host=settings.mcp_host,
        port=settings.mcp_port,
        streamable_http_path="/mcp",
        log_level=settings.log_level,  # type: ignore[arg-type]
        stateless_http=True,
        json_response=True,
    )
    register_product_tools(mcp, product_client)
    _register_health_route(mcp)
    return mcp, product_client


def _register_health_route(mcp: FastMCP) -> None:
    """Expose GET /health for process liveness (not a product catalog call)."""

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request: Request) -> JSONResponse:
        payload: dict[str, Any] = {
            "status": "ok",
            "service": "hbntory-product-mcp",
            "read_only": True,
        }
        return JSONResponse(payload)


def configure_logging(level: str = "INFO") -> None:
    """Configure basic logging without leaking secrets."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )


def main(argv: list[str] | None = None) -> None:
    """Start the Product MCP Server from environment configuration."""

    del argv  # Reserved for future CLI flags; configuration uses env vars.
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    logger.info(
        "Starting Product MCP Server transport=%s host=%s port=%s",
        settings.mcp_transport,
        settings.mcp_host,
        settings.mcp_port,
    )

    mcp, client = create_mcp_server(settings)
    try:
        mcp.run(transport=settings.mcp_transport)  # type: ignore[arg-type]
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":
    main()
