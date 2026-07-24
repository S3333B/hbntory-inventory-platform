"""MCP adapters for read-only stock tools.

Handlers accept an injectable stock repository so unit tests can run against a
fake or an isolated SQLite database without PostgreSQL or the network.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from product_mcp_server.app.stock_exceptions import StockQueryError
from product_mcp_server.app.stock_query import (
    check_shopping_list,
    get_branch_stock,
    get_product_stock,
)
from product_mcp_server.app.stock_repository import SupportsStockRepository
from product_mcp_server.app.tools import error_result, success_result

logger = logging.getLogger(__name__)

STOCK_TOOL_NAMES = (
    "get_product_stock",
    "get_branch_stock",
    "check_shopping_list",
)


def stock_error_to_result(exc: StockQueryError) -> dict[str, Any]:
    """Map a stock query exception to a structured MCP error result."""

    return error_result(exc.code, exc.message)


def get_product_stock_handler(
    repository: SupportsStockRepository,
    *,
    product_id: object,
) -> dict[str, Any]:
    """Handler for get_product_stock."""

    try:
        data = get_product_stock(repository, product_id)
        return success_result(data)
    except StockQueryError as exc:
        logger.info("get_product_stock failed with %s: %s", exc.code, exc.message)
        return stock_error_to_result(exc)
    except Exception as exc:
        logger.error(
            "Unexpected error in get_product_stock (%s)",
            type(exc).__name__,
        )
        return error_result(
            "INTERNAL_ERROR",
            "An unexpected error occurred while retrieving product stock.",
        )


def get_branch_stock_handler(
    repository: SupportsStockRepository,
    *,
    branch: object,
) -> dict[str, Any]:
    """Handler for get_branch_stock."""

    try:
        data = get_branch_stock(repository, branch)
        return success_result(data)
    except StockQueryError as exc:
        logger.info("get_branch_stock failed with %s: %s", exc.code, exc.message)
        return stock_error_to_result(exc)
    except Exception as exc:
        logger.error(
            "Unexpected error in get_branch_stock (%s)",
            type(exc).__name__,
        )
        return error_result(
            "INTERNAL_ERROR",
            "An unexpected error occurred while retrieving branch stock.",
        )


def check_shopping_list_handler(
    repository: SupportsStockRepository,
    *,
    items: object,
) -> dict[str, Any]:
    """Handler for check_shopping_list."""

    try:
        data = check_shopping_list(repository, items)
        return success_result(data)
    except StockQueryError as exc:
        logger.info("check_shopping_list failed with %s: %s", exc.code, exc.message)
        return stock_error_to_result(exc)
    except Exception as exc:
        logger.error(
            "Unexpected error in check_shopping_list (%s)",
            type(exc).__name__,
        )
        return error_result(
            "INTERNAL_ERROR",
            "An unexpected error occurred while checking the shopping list.",
        )


def register_stock_tools(
    mcp: FastMCP,
    repository: SupportsStockRepository,
) -> list[str]:
    """Register read-only stock tools on a FastMCP server."""

    @mcp.tool(
        name="get_product_stock",
        description=(
            "Return positive stock quantities for one product across HBntory "
            "branches. Input: product_id (strictly positive integer external "
            "product identifier). Output includes external_product_id, "
            "total_quantity, and branches with branch_id, branch_name, and "
            "quantity. Zero quantities are omitted. Read-only: never modifies "
            "stock and never invents quantities. Does not apply Backoffice "
            "admin/common roles; intended for the AI Query Service only."
        ),
    )
    def get_product_stock_tool(product_id: int) -> dict[str, Any]:
        return get_product_stock_handler(repository, product_id=product_id)

    @mcp.tool(
        name="get_branch_stock",
        description=(
            "Return positive stock quantities for one HBntory branch. Input: "
            "branch as a positive integer branch_id or a non-empty branch name "
            "(case-insensitive exact match). Output includes branch_id, "
            "branch_name, and stocks with external_product_id and quantity only "
            "(no product names, prices, or descriptions). Read-only. Does not "
            "apply Backoffice admin/common roles; intended for the AI Query "
            "Service only."
        ),
    )
    def get_branch_stock_tool(branch: str | int) -> dict[str, Any]:
        return get_branch_stock_handler(repository, branch=branch)

    @mcp.tool(
        name="check_shopping_list",
        description=(
            "Check whether a shopping list can be fulfilled from one or more "
            "HBntory branches. Input: items — a non-empty list of objects with "
            "product_id and quantity (both strictly positive integers). "
            "Duplicate product_id entries are merged by summing quantities. "
            "Returns whether a single branch can fulfill the list, candidate "
            "branches, a deterministic multi-branch fulfillment plan when "
            "needed, and missing items when stock is insufficient. Read-only. "
            "Does not apply Backoffice admin/common roles."
        ),
    )
    def check_shopping_list_tool(
        items: list[dict[str, int]],
    ) -> dict[str, Any]:
        return check_shopping_list_handler(repository, items=items)

    get_product_stock_tool.__hbntory_handler__ = get_product_stock_handler  # type: ignore[attr-defined]
    get_branch_stock_tool.__hbntory_handler__ = get_branch_stock_handler  # type: ignore[attr-defined]
    check_shopping_list_tool.__hbntory_handler__ = check_shopping_list_handler  # type: ignore[attr-defined]

    return list(STOCK_TOOL_NAMES)
