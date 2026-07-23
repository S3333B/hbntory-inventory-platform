"""Stable data shapes exchanged with the External Product API."""

from __future__ import annotations

from typing import Any, TypedDict


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
    """Return a product dict without inventing missing catalog fields.

    Only known official fields are kept. Nested supplier data is preserved
    when present on detail responses.
    """

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

    count = payload.get("count", len(results))
    limit = payload.get("limit", len(results))
    offset = payload.get("offset", 0)

    if not isinstance(count, int):
        raise TypeError("Product list count must be an integer.")
    if not isinstance(limit, int):
        raise TypeError("Product list limit must be an integer.")
    if not isinstance(offset, int):
        raise TypeError("Product list offset must be an integer.")

    return {
        "count": count,
        "limit": limit,
        "offset": offset,
        "results": results,
    }
