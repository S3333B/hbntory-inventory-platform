"""MCP product tools (read-only).

Tool handlers accept an injectable ProductApiClient so automated tests never
require the network. Errors are returned as structured MCP results; no stack
traces or secrets are exposed to the agent.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from mcp.server.fastmcp import FastMCP

from product_mcp_server.app.exceptions import ProductApiError
from product_mcp_server.app.models import ProductDict, ProductListDict

logger = logging.getLogger(__name__)


class SupportsProductApi(Protocol):
    """Injectable product catalog client interface (real or fake)."""

    def list_products(self, **kwargs: Any) -> ProductListDict: ...

    def get_product(self, id_or_sku: str | int) -> ProductDict: ...


def success_result(data: Any) -> dict[str, Any]:
    """Build a stable successful MCP tool payload."""

    return {"status": "success", "data": data}


def error_result(code: str, message: str) -> dict[str, Any]:
    """Build a stable error MCP tool payload."""

    return {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
    }


def product_api_error_to_result(exc: ProductApiError) -> dict[str, Any]:
    """Map a client exception to a structured MCP error result."""

    return error_result(exc.code, exc.message)


def list_products_handler(
    client: SupportsProductApi,
    *,
    q: str | None = None,
    category: str | None = None,
    supplier_id: str | None = None,
    include_discontinued: bool | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int | None = None,
    offset: int | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    """List products from the external Product API (handler for tests/tools)."""

    try:
        product_list = client.list_products(
            q=q,
            category=category,
            supplier_id=supplier_id,
            include_discontinued=include_discontinued,
            min_price=min_price,
            max_price=max_price,
            limit=limit,
            offset=offset,
            sort=sort,
        )
        return success_result(product_list)
    except ProductApiError as exc:
        logger.info("list_products failed with %s: %s", exc.code, exc.message)
        return product_api_error_to_result(exc)
    except Exception:
        logger.exception("Unexpected error in list_products")
        return error_result(
            "INTERNAL_ERROR",
            "An unexpected error occurred while listing products.",
        )


def get_product_details_handler(
    client: SupportsProductApi,
    *,
    id_or_sku: str | int,
) -> dict[str, Any]:
    """Get one product by id or SKU (handler for tests/tools)."""

    try:
        product = client.get_product(id_or_sku)
        return success_result(product)
    except ProductApiError as exc:
        logger.info(
            "get_product_details failed with %s: %s",
            exc.code,
            exc.message,
        )
        return product_api_error_to_result(exc)
    except Exception:
        logger.exception("Unexpected error in get_product_details")
        return error_result(
            "INTERNAL_ERROR",
            "An unexpected error occurred while retrieving the product.",
        )


def register_product_tools(
    mcp: FastMCP,
    client: SupportsProductApi,
) -> list[str]:
    """Register read-only product tools on a FastMCP server.

    Returns the registered tool names for introspection and tests.
    """

    @mcp.tool(
        name="list_products",
        description=(
            "List products from the official External Product API catalog. "
            "Supports optional official filters and pagination (q, category, "
            "supplier_id, include_discontinued, min_price, max_price, limit, "
            "offset, sort). Returns a structured success payload with count, "
            "limit, offset, and results. An empty results list is valid. "
            "Read-only: never invents products and never writes data."
        ),
    )
    def list_products(
        q: str | None = None,
        category: str | None = None,
        supplier_id: str | None = None,
        include_discontinued: bool | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
    ) -> dict[str, Any]:
        return list_products_handler(
            client,
            q=q,
            category=category,
            supplier_id=supplier_id,
            include_discontinued=include_discontinued,
            min_price=min_price,
            max_price=max_price,
            limit=limit,
            offset=offset,
            sort=sort,
        )

    @mcp.tool(
        name="get_product_details",
        description=(
            "Retrieve one product from the official External Product API by "
            "numeric id or SKU (for example 1 or HB-LAP-1001). Returns the "
            "official product fields when found. Returns a structured "
            "PRODUCT_NOT_FOUND error when the product does not exist. "
            "Rejects empty or invalid identifiers. Read-only: never invents "
            "product data and never writes data."
        ),
    )
    def get_product_details(id_or_sku: str) -> dict[str, Any]:
        return get_product_details_handler(client, id_or_sku=id_or_sku)

    # Keep a stable export of handlers for unit tests without MCP transport.
    list_products.__hbntory_handler__ = list_products_handler  # type: ignore[attr-defined]
    get_product_details.__hbntory_handler__ = get_product_details_handler  # type: ignore[attr-defined]

    return ["list_products", "get_product_details"]


def registered_write_tools() -> list[str]:
    """Document that no write tools are exposed by this server."""

    return []
