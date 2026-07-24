"""Product MCP Server entry point.

Exposes read-only product tools (External Product API) and read-only stock
tools (controlled SQLAlchemy queries against HBntory PostgreSQL) over MCP
Streamable HTTP (default) or stdio.

Security boundary:
- public MCP tools are intended for the AI Query Service only;
- they do not apply Backoffice admin/common roles;
- stock tools are strictly read-only and never accept arbitrary SQL;
- password hashes, sessions, secrets, and internal SQL errors are never exposed.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request
from starlette.responses import JSONResponse

from product_mcp_server.app.config import Settings
from product_mcp_server.app.db import create_stock_engine, create_stock_session_factory
from product_mcp_server.app.product_api_client import ProductApiClient
from product_mcp_server.app.stock_repository import (
    SqlAlchemyStockRepository,
    SupportsStockRepository,
)
from product_mcp_server.app.stock_tools import register_stock_tools
from product_mcp_server.app.tools import SupportsProductApi, register_product_tools

logger = logging.getLogger(__name__)

SERVER_INSTRUCTIONS = (
    "HBntory Product MCP Server. Read-only tools for the official External "
    "Product API catalog and controlled read-only HBntory stock queries. "
    "Does not store product catalog data, does not modify stock, never accepts "
    "arbitrary SQL, and does not apply Backoffice admin/common roles. Product "
    "tools: list_products, get_product_details. Stock tools: get_product_stock, "
    "get_branch_stock, check_shopping_list."
)


def create_mcp_server(
    settings: Settings,
    *,
    client: Optional[SupportsProductApi] = None,
    stock_repository: Optional[SupportsStockRepository] = None,
    session_factory: Optional[sessionmaker[Session]] = None,
    engine: Optional[Engine] = None,
) -> tuple[FastMCP, SupportsProductApi, SupportsStockRepository | None, Engine | None]:
    """Build a configured FastMCP server with product and stock tools.

    Stock tools are registered when ``stock_repository`` is provided, or when
    ``session_factory`` / ``engine`` / ``settings.database_url`` can build one.
    Tests inject a fake repository or an isolated SQLite session factory.
    """

    product_client: SupportsProductApi = client or ProductApiClient(
        base_url=settings.product_api_url,
        timeout=settings.product_api_timeout,
    )

    owned_engine: Engine | None = None
    repository = stock_repository
    if repository is None:
        factory = session_factory
        if factory is None:
            database_url = settings.database_url
            if database_url:
                owned_engine = engine or create_stock_engine(database_url)
                factory = create_stock_session_factory(owned_engine)
            elif engine is not None:
                owned_engine = engine
                factory = create_stock_session_factory(engine)
        if factory is not None:
            repository = SqlAlchemyStockRepository(factory)

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
    if repository is not None:
        register_stock_tools(mcp, repository)
    else:
        logger.warning(
            "Stock tools are not registered because DATABASE_URL is unset "
            "and no stock repository was injected."
        )
    _register_health_route(mcp, stock_enabled=repository is not None)
    return mcp, product_client, repository, owned_engine


def _register_health_route(mcp: FastMCP, *, stock_enabled: bool) -> None:
    """Expose GET /health for process liveness (not a catalog or stock call)."""

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request: Request) -> JSONResponse:
        payload: dict[str, Any] = {
            "status": "ok",
            "service": "hbntory-product-mcp",
            "read_only": True,
            "stock_tools_enabled": stock_enabled,
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

    if not settings.database_url:
        raise SystemExit(
            "DATABASE_URL is required to enable read-only stock tools. "
            "Set it to the HBntory PostgreSQL URL (see .env.example)."
        )

    logger.info(
        "Starting Product MCP Server transport=%s host=%s port=%s stock_tools=enabled",
        settings.mcp_transport,
        settings.mcp_host,
        settings.mcp_port,
    )

    mcp, client, _repository, engine = create_mcp_server(settings)
    try:
        mcp.run(transport=settings.mcp_transport)  # type: ignore[arg-type]
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
