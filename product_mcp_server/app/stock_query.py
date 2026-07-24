"""Deterministic read-only stock query logic.

This module contains no MCP transport concerns and no write operations. The
shopping-list multi-branch allocator is intentionally simple, stable, and fully
tested rather than an optimal mathematical solver.
"""

from __future__ import annotations

from typing import Any

from product_mcp_server.app.stock_exceptions import (
    BranchNotFoundError,
    InvalidStockArgumentError,
    StockNotFoundError,
    StockQueryError,
)
from product_mcp_server.app.stock_repository import (
    StockLine,
    SupportsStockRepository,
)


def require_positive_int(name: str, value: object) -> int:
    """Validate a strictly positive integer (booleans rejected)."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InvalidStockArgumentError(
            f"{name} must be a strictly positive integer."
        )
    return value


def normalize_shopping_items(items: object) -> list[dict[str, int]]:
    """Validate shopping-list items and merge duplicate product_id values.

    Duplicate products are summed after each entry is validated. The merged list
    is ordered by ascending product_id for deterministic later processing.
    """

    if items is None or not isinstance(items, list):
        raise InvalidStockArgumentError("items must be a non-empty list.")
    if len(items) == 0:
        raise InvalidStockArgumentError("items must be a non-empty list.")

    merged: dict[int, int] = {}
    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, dict):
            raise InvalidStockArgumentError(
                f"items[{index}] must be an object with product_id and quantity."
            )
        # Accept both product_id (tool contract) and external_product_id aliases.
        if "product_id" in raw_item:
            product_raw = raw_item["product_id"]
        elif "external_product_id" in raw_item:
            product_raw = raw_item["external_product_id"]
        else:
            raise InvalidStockArgumentError(
                f"items[{index}] must include product_id."
            )
        if "quantity" not in raw_item:
            raise InvalidStockArgumentError(
                f"items[{index}] must include quantity."
            )
        product_id = require_positive_int(
            f"items[{index}].product_id",
            product_raw,
        )
        quantity = require_positive_int(
            f"items[{index}].quantity",
            raw_item["quantity"],
        )
        merged[product_id] = merged.get(product_id, 0) + quantity

    return [
        {"product_id": product_id, "quantity": quantity}
        for product_id, quantity in sorted(merged.items())
    ]


def resolve_branch_reference(
    repository: SupportsStockRepository,
    branch: object,
) -> dict[str, Any]:
    """Resolve a branch by positive integer id or non-empty name."""

    if isinstance(branch, bool) or branch is None:
        raise InvalidStockArgumentError(
            "branch must be a positive integer id or a non-empty name."
        )

    if isinstance(branch, int):
        if branch < 1:
            raise InvalidStockArgumentError(
                "branch must be a positive integer id or a non-empty name."
            )
        record = repository.get_branch_by_id(branch)
        if record is None:
            raise BranchNotFoundError()
        return {
            "branch_id": record.branch_id,
            "branch_name": record.branch_name,
        }

    if isinstance(branch, str):
        name = branch.strip()
        if not name:
            raise InvalidStockArgumentError("branch name must not be empty.")
        record = repository.get_branch_by_name(name)
        if record is None:
            raise BranchNotFoundError()
        return {
            "branch_id": record.branch_id,
            "branch_name": record.branch_name,
        }

    raise InvalidStockArgumentError(
        "branch must be a positive integer id or a non-empty name."
    )


def get_product_stock(
    repository: SupportsStockRepository,
    product_id: object,
) -> dict[str, Any]:
    """Return positive stock for one product across branches."""

    external_product_id = require_positive_int("product_id", product_id)
    lines = repository.list_product_stock(external_product_id)
    branches = [
        {
            "branch_id": line.branch_id,
            "branch_name": line.branch_name,
            "quantity": line.quantity,
        }
        for line in lines
        if line.quantity > 0
    ]
    total_quantity = sum(item["quantity"] for item in branches)
    if total_quantity == 0:
        # Controlled empty result: no invented availability.
        raise StockNotFoundError()
    return {
        "external_product_id": external_product_id,
        "total_quantity": total_quantity,
        "branches": branches,
    }


def get_branch_stock(
    repository: SupportsStockRepository,
    branch: object,
) -> dict[str, Any]:
    """Return positive product quantities for one branch."""

    resolved = resolve_branch_reference(repository, branch)
    lines = repository.list_branch_stock(resolved["branch_id"])
    stocks = [
        {
            "external_product_id": line.external_product_id,
            "quantity": line.quantity,
        }
        for line in lines
        if line.quantity > 0
    ]
    return {
        "branch_id": resolved["branch_id"],
        "branch_name": resolved["branch_name"],
        "stocks": stocks,
    }


def check_shopping_list(
    repository: SupportsStockRepository,
    items: object,
) -> dict[str, Any]:
    """Evaluate whether one or more branches can satisfy a shopping list.

    Algorithm (deterministic):

    1. Validate items and merge duplicate product_id values by summing quantities.
    2. Load all positive stock lines for the requested products.
    3. Single-branch candidates: every branch that holds enough of every product,
       ordered by ascending branch_id.
    4. If at least one single-branch candidate exists, return those candidates and
       no multi-branch plan is required.
    5. Otherwise, multi-branch allocation for each product (ascending product_id):
       - remaining need starts at the requested quantity;
       - candidate branches for that product are ordered by:
         (a) quantity descending,
         (b) branch_id ascending as a stable tie-breaker;
       - allocate greedily until the need is zero or stock is exhausted.
    6. Group allocations by branch_id ascending to form the fulfillment plan.
    7. Any product still short is reported in missing_items.

    The allocator is stable and testable; it is not a perfect optimizer.
    """

    normalized_items = normalize_shopping_items(items)
    product_ids = [item["product_id"] for item in normalized_items]
    requested = {item["product_id"]: item["quantity"] for item in normalized_items}

    lines = repository.list_stock_for_products(product_ids)
    availability = _build_availability(lines)

    single_candidates = _single_branch_candidates(requested, availability)
    if single_candidates:
        return {
            "requested_items": normalized_items,
            "single_branch_possible": True,
            "single_branch_candidates": single_candidates,
            "multi_branch_possible": False,
            "fulfillable": True,
            "fulfillment_plan": [
                {
                    "branch_id": candidate["branch_id"],
                    "branch_name": candidate["branch_name"],
                    "items": [
                        {
                            "product_id": product_id,
                            "quantity": requested[product_id],
                        }
                        for product_id in sorted(requested)
                    ],
                }
                # The first candidate is a valid single-branch plan; others remain
                # listed so the agent can choose among equivalent branches.
                for candidate in single_candidates[:1]
            ],
            "missing_items": [],
        }

    plan, missing = _multi_branch_allocate(requested, availability)
    fulfillable = len(missing) == 0 and len(plan) > 0
    # Multi-branch is only meaningful when no single branch can fulfill.
    multi_possible = fulfillable
    return {
        "requested_items": normalized_items,
        "single_branch_possible": False,
        "single_branch_candidates": [],
        "multi_branch_possible": multi_possible,
        "fulfillable": fulfillable,
        "fulfillment_plan": plan if fulfillable else [],
        "missing_items": missing,
    }


def _build_availability(
    lines: list[StockLine],
) -> dict[int, dict[int, tuple[str, int]]]:
    """Map product_id -> branch_id -> (branch_name, quantity)."""

    availability: dict[int, dict[int, tuple[str, int]]] = {}
    for line in lines:
        if line.quantity <= 0:
            continue
        product_map = availability.setdefault(line.external_product_id, {})
        product_map[line.branch_id] = (line.branch_name, line.quantity)
    return availability


def _single_branch_candidates(
    requested: dict[int, int],
    availability: dict[int, dict[int, tuple[str, int]]],
) -> list[dict[str, Any]]:
    branch_names: dict[int, str] = {}
    for product_map in availability.values():
        for branch_id, (branch_name, _qty) in product_map.items():
            branch_names.setdefault(branch_id, branch_name)

    candidates: list[dict[str, Any]] = []
    for branch_id in sorted(branch_names):
        if all(
            availability.get(product_id, {}).get(branch_id, ("", 0))[1] >= quantity
            for product_id, quantity in requested.items()
        ):
            candidates.append(
                {
                    "branch_id": branch_id,
                    "branch_name": branch_names[branch_id],
                }
            )
    return candidates


def _multi_branch_allocate(
    requested: dict[int, int],
    availability: dict[int, dict[int, tuple[str, int]]],
) -> tuple[list[dict[str, Any]], list[dict[str, int]]]:
    """Greedy multi-branch allocation with a stable selection order."""

    # branch_id -> product_id -> allocated quantity
    allocations: dict[int, dict[int, int]] = {}
    branch_names: dict[int, str] = {}
    missing: list[dict[str, int]] = []

    for product_id in sorted(requested):
        need = requested[product_id]
        product_map = availability.get(product_id, {})
        # Prefer larger available quantity, then stable branch_id order.
        ordered_branches = sorted(
            product_map.items(),
            key=lambda item: (-item[1][1], item[0]),
        )
        remaining = need
        available_total = 0
        for branch_id, (branch_name, quantity) in ordered_branches:
            if remaining <= 0:
                break
            take = min(remaining, quantity)
            if take <= 0:
                continue
            branch_names[branch_id] = branch_name
            branch_alloc = allocations.setdefault(branch_id, {})
            branch_alloc[product_id] = branch_alloc.get(product_id, 0) + take
            remaining -= take
            available_total += take
        if remaining > 0:
            missing.append(
                {
                    "product_id": product_id,
                    "requested_quantity": need,
                    "available_quantity": available_total,
                    "missing_quantity": remaining,
                }
            )

    plan: list[dict[str, Any]] = []
    for branch_id in sorted(allocations):
        items = [
            {"product_id": product_id, "quantity": quantity}
            for product_id, quantity in sorted(allocations[branch_id].items())
        ]
        plan.append(
            {
                "branch_id": branch_id,
                "branch_name": branch_names[branch_id],
                "items": items,
            }
        )
    return plan, missing


def stock_query_error_to_payload(exc: StockQueryError) -> dict[str, str]:
    """Expose only the stable public code and message."""

    return {"code": exc.code, "message": exc.message}
