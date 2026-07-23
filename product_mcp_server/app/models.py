"""Stable data shapes exchanged with the External Product API."""

from __future__ import annotations

from typing import Any, TypedDict

_REQUIRED_PRODUCT_FIELDS = ("id", "sku", "name")


class ProductDict(TypedDict, total=False):
    """Product fields returned by the official catalog API."""

    id: int
    sku: str
    name: str
    description: str
    category: str
    brand: str
    supplier_id: str
    supplier_name: str
    unit_price: float
    currency: str
    discontinued: bool
    weight_kg: float
    tags: list[str]
    updated_at: str
    supplier: dict[str, Any]


class ProductListDict(TypedDict):
    """Paginated product list returned by GET /api/v1/products."""

    count: int
    limit: int
    offset: int
    results: list[ProductDict]


def normalize_product(payload: dict[str, Any]) -> ProductDict:
    """Validate and return official product fields without inventing data.

    Only known official fields are kept. Nested supplier data is preserved
    when present on detail responses.
    """

    if not isinstance(payload, dict):
        raise TypeError("Product payload must be a JSON object.")

    for field in _REQUIRED_PRODUCT_FIELDS:
        if field not in payload:
            raise ValueError(f"Product payload must include {field}.")

    product_id = payload["id"]
    if (
        not isinstance(product_id, int)
        or isinstance(product_id, bool)
        or product_id <= 0
    ):
        raise TypeError("Product id must be a positive integer.")

    for field in (
        "sku",
        "name",
        "description",
        "category",
        "brand",
        "supplier_id",
        "supplier_name",
        "currency",
        "updated_at",
    ):
        if field in payload and not isinstance(payload[field], str):
            raise TypeError(f"Product {field} must be a string.")
    if not payload["sku"].strip() or not payload["name"].strip():
        raise ValueError("Product sku and name must not be empty.")

    for field in ("unit_price", "weight_kg"):
        value = payload.get(field)
        if value is not None and (
            not isinstance(value, (int, float)) or isinstance(value, bool)
        ):
            raise TypeError(f"Product {field} must be a number.")

    discontinued = payload.get("discontinued")
    if discontinued is not None and not isinstance(discontinued, bool):
        raise TypeError("Product discontinued must be a boolean.")

    tags = payload.get("tags")
    if tags is not None and (
        not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags)
    ):
        raise TypeError("Product tags must be an array of strings.")

    supplier = payload.get("supplier")
    if supplier is not None and not isinstance(supplier, dict):
        raise TypeError("Product supplier must be a JSON object.")

    product: ProductDict = {}
    for key in (
        "id",
        "sku",
        "name",
        "description",
        "category",
        "brand",
        "supplier_id",
        "supplier_name",
        "unit_price",
        "currency",
        "discontinued",
        "weight_kg",
        "tags",
        "updated_at",
        "supplier",
    ):
        if key in payload:
            product[key] = payload[key]  # type: ignore[literal-required]
    return product


def normalize_product_list(payload: dict[str, Any]) -> ProductListDict:
    """Validate and normalize a product list payload from the official API."""

    if not isinstance(payload, dict):
        raise TypeError("Product list payload must be a JSON object.")

    results_raw = payload.get("results")
    if not isinstance(results_raw, list):
        raise TypeError("Product list payload must include a results array.")

    results: list[ProductDict] = []
    for item in results_raw:
        if not isinstance(item, dict):
            raise TypeError("Each product in results must be a JSON object.")
        results.append(normalize_product(item))

    for field in ("count", "limit", "offset"):
        if field not in payload:
            raise ValueError(f"Product list payload must include {field}.")

    count = payload["count"]
    limit = payload["limit"]
    offset = payload["offset"]

    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise TypeError("Product list count must be a non-negative integer.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise TypeError("Product list limit must be an integer from 1 to 100.")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise TypeError("Product list offset must be a non-negative integer.")
    if count < len(results):
        raise ValueError("Product list count cannot be smaller than its results.")

    return {
        "count": count,
        "limit": limit,
        "offset": offset,
        "results": results,
    }
