"""Network-free test doubles for the Product MCP Server."""

from __future__ import annotations

from typing import Any, Callable

import httpx

from product_mcp_server.app.exceptions import (
    InvalidProductIdentifierError,
    ProductApiConnectionError,
    ProductApiResponseError,
    ProductApiTimeoutError,
    ProductNotFoundError,
)
from product_mcp_server.app.models import ProductDict, ProductListDict
from product_mcp_server.app.product_api_client import validate_product_identifier


SAMPLE_PRODUCT: ProductDict = {
    "id": 1,
    "sku": "HB-LAP-1001",
    "name": "Holberton Student Laptop 14",
    "description": "Training catalog item for HBntory integration.",
    "category": "Laptops",
    "brand": "Holberton",
    "supplier_id": "SUP-HBT-001",
    "supplier_name": "Holberton Tools Co.",
    "unit_price": 799.0,
    "currency": "USD",
    "discontinued": False,
    "weight_kg": 1.35,
    "tags": ["student", "portable", "linux-ready"],
    "updated_at": "2026-05-22T12:00:00Z",
}

SAMPLE_PRODUCT_DETAIL: ProductDict = {
    **SAMPLE_PRODUCT,
    "supplier": {
        "id": "SUP-HBT-001",
        "name": "Holberton Tools Co.",
        "contact_email": "catalog@holberton-tools.example",
        "country": "US",
        "lead_time_days": 5,
        "reliability_score": 0.97,
    },
}


class FakeProductApiClient:
    """Injectable client that records calls and never uses the network."""

    def __init__(
        self,
        *,
        products: list[ProductDict] | None = None,
        list_error: Exception | None = None,
        get_error: Exception | None = None,
    ) -> None:
        self.products = (
            list(products) if products is not None else [dict(SAMPLE_PRODUCT)]
        )
        self.list_error = list_error
        self.get_error = get_error
        self.list_calls: list[dict[str, Any]] = []
        self.get_calls: list[str | int] = []

    def list_products(self, **kwargs: Any) -> ProductListDict:
        self.list_calls.append(kwargs)
        if self.list_error is not None:
            raise self.list_error
        limit = kwargs.get("limit")
        offset = kwargs.get("offset") or 0
        results = list(self.products)
        if limit is not None:
            results = results[offset : offset + limit]
        elif offset:
            results = results[offset:]
        return {
            "count": len(self.products),
            "limit": limit if limit is not None else 20,
            "offset": offset if offset is not None else 0,
            "results": results,
        }

    def get_product(self, id_or_sku: str | int) -> ProductDict:
        self.get_calls.append(id_or_sku)
        if self.get_error is not None:
            raise self.get_error
        identifier = validate_product_identifier(id_or_sku)
        for product in self.products:
            if str(product.get("id")) == identifier or product.get("sku") == identifier:
                return dict(product)
        raise ProductNotFoundError("Product not found.")

    def close(self) -> None:
        return None


def build_mock_transport(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.MockTransport:
    """Wrap a request handler in httpx.MockTransport (no real network)."""

    return httpx.MockTransport(handler)


def json_response(
    status_code: int,
    payload: Any,
) -> httpx.Response:
    """Build an httpx.Response with a JSON body for MockTransport handlers."""

    return httpx.Response(status_code, json=payload)


__all__ = [
    "FakeProductApiClient",
    "SAMPLE_PRODUCT",
    "SAMPLE_PRODUCT_DETAIL",
    "build_mock_transport",
    "json_response",
    "InvalidProductIdentifierError",
    "ProductApiConnectionError",
    "ProductApiResponseError",
    "ProductApiTimeoutError",
    "ProductNotFoundError",
]
