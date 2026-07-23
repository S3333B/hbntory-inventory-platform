"""Reusable HTTP client for the official External Product API.

This client is an internal component of the Product MCP Server. It is not the
future public web client. It performs read-only GET requests only and never
persists catalog data.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Mapping, Protocol
from urllib.parse import quote

import httpx

from product_mcp_server.app.exceptions import (
    InvalidProductIdentifierError,
    ProductApiConnectionError,
    ProductApiResponseError,
    ProductApiTimeoutError,
    ProductNotFoundError,
)
from product_mcp_server.app.models import (
    ProductDict,
    ProductListDict,
    normalize_product,
    normalize_product_list,
)

logger = logging.getLogger(__name__)

# Official list query parameters supported by GET /api/v1/products.
_LIST_PARAM_NAMES = (
    "q",
    "category",
    "supplier_id",
    "include_discontinued",
    "min_price",
    "max_price",
    "limit",
    "offset",
    "sort",
)

# Reject path injection and empty identifiers before calling the API.
_INVALID_ID_PATTERN = re.compile(r"[/?#\s\\]")


class HttpClientProtocol(Protocol):
    """Minimal HTTP interface used by ProductApiClient (for injection)."""

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        timeout: float | httpx.Timeout | None = None,
    ) -> httpx.Response: ...

    def close(self) -> None: ...


def validate_product_identifier(id_or_sku: str | int | None) -> str:
    """Normalize and validate a product id or SKU for path usage.

    Raises:
        InvalidProductIdentifierError: when the value is empty or unsafe.
    """

    if id_or_sku is None:
        raise InvalidProductIdentifierError(
            "A product id or SKU is required."
        )

    if isinstance(id_or_sku, bool):
        # bool is a subclass of int; reject it as a product identifier.
        raise InvalidProductIdentifierError(
            "The product identifier is invalid."
        )

    if isinstance(id_or_sku, int):
        if id_or_sku <= 0:
            raise InvalidProductIdentifierError(
                "The product identifier must be a positive integer or a SKU."
            )
        return str(id_or_sku)

    if not isinstance(id_or_sku, str):
        raise InvalidProductIdentifierError(
            "The product identifier must be a string or a positive integer."
        )

    value = id_or_sku.strip()
    if not value:
        raise InvalidProductIdentifierError(
            "A product id or SKU is required."
        )
    if _INVALID_ID_PATTERN.search(value):
        raise InvalidProductIdentifierError(
            "The product identifier contains invalid characters."
        )
    return value


class ProductApiClient:
    """Read-only HTTP client for the official External Product API."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 5.0,
        http_client: HttpClientProtocol | None = None,
    ) -> None:
        if not base_url or not str(base_url).strip():
            raise ValueError("base_url must not be empty.")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero.")

        self._base_url = str(base_url).rstrip("/")
        self._timeout = float(timeout)
        self._owns_client = http_client is None
        self._http: HttpClientProtocol = http_client or httpx.Client(
            timeout=self._timeout,
            headers={"Accept": "application/json"},
        )

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout(self) -> float:
        return self._timeout

    def close(self) -> None:
        """Close the underlying HTTP client when this instance owns it."""

        if self._owns_client:
            self._http.close()

    def __enter__(self) -> ProductApiClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def list_products(
        self,
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
    ) -> ProductListDict:
        """List products via GET /api/v1/products.

        Only official query parameters are forwarded. An empty ``results``
        array is a valid successful response, distinct from connection errors.
        """

        params: dict[str, Any] = {}
        if q is not None and str(q).strip() != "":
            params["q"] = str(q).strip()
        if category is not None and str(category).strip() != "":
            params["category"] = str(category).strip()
        if supplier_id is not None and str(supplier_id).strip() != "":
            params["supplier_id"] = str(supplier_id).strip()
        if include_discontinued is not None:
            params["include_discontinued"] = (
                "true" if include_discontinued else "false"
            )
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if limit is not None:
            if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
                raise ProductApiResponseError(
                    "limit must be a positive integer.",
                    code="INVALID_ARGUMENT",
                )
            params["limit"] = limit
        if offset is not None:
            if (
                not isinstance(offset, int)
                or isinstance(offset, bool)
                or offset < 0
            ):
                raise ProductApiResponseError(
                    "offset must be a non-negative integer.",
                    code="INVALID_ARGUMENT",
                )
            params["offset"] = offset
        if sort is not None and str(sort).strip() != "":
            params["sort"] = str(sort).strip()

        # Ensure unused official params stay documented for readers.
        assert set(params).issubset(set(_LIST_PARAM_NAMES))

        payload = self._request_json("GET", "/api/v1/products", params=params)
        try:
            return normalize_product_list(payload)
        except (TypeError, ValueError) as exc:
            logger.warning("Invalid product list payload from Product API: %s", exc)
            raise ProductApiResponseError(
                "The product service returned an invalid product list."
            ) from exc

    def get_product(self, id_or_sku: str | int) -> ProductDict:
        """Retrieve one product via GET /api/v1/products/{id_or_sku}."""

        identifier = validate_product_identifier(id_or_sku)
        # quote keeps SKU characters safe in the path without inventing data.
        path = f"/api/v1/products/{quote(identifier, safe='-_.')}"
        payload = self._request_json("GET", path, not_found_is_product=True)
        if not isinstance(payload, dict):
            raise ProductApiResponseError(
                "The product service returned an invalid product payload."
            )
        try:
            product = normalize_product(payload)
        except (TypeError, ValueError) as exc:
            raise ProductApiResponseError(
                "The product service returned an invalid product payload."
            ) from exc
        if "id" not in product and "sku" not in product:
            raise ProductApiResponseError(
                "The product service returned an incomplete product payload."
            )
        return product

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        not_found_is_product: bool = False,
    ) -> Any:
        if method != "GET":
            # Defensive guard: this client is strictly read-only.
            raise ProductApiResponseError(
                "Only GET operations are allowed against the Product API.",
                code="INVALID_ARGUMENT",
            )

        url = f"{self._base_url}{path}"
        try:
            response = self._http.get(url, params=params, timeout=self._timeout)
        except httpx.TimeoutException as exc:
            logger.warning("Product API timeout for %s %s", method, path)
            raise ProductApiTimeoutError() from exc
        except httpx.RequestError as exc:
            logger.warning(
                "Product API connection error for %s %s: %s",
                method,
                path,
                type(exc).__name__,
            )
            raise ProductApiConnectionError() from exc

        if response.status_code == 404 and not_found_is_product:
            message = self._extract_error_message(
                response,
                default="Product not found.",
            )
            raise ProductNotFoundError(message)

        if response.status_code >= 500:
            logger.warning(
                "Product API server error %s for %s %s",
                response.status_code,
                method,
                path,
            )
            raise ProductApiConnectionError(
                "Product information is temporarily unavailable."
            )

        if response.status_code != 200:
            logger.warning(
                "Unexpected Product API status %s for %s %s",
                response.status_code,
                method,
                path,
            )
            raise ProductApiResponseError(
                "The product service returned an unexpected HTTP status."
            )

        try:
            return response.json()
        except ValueError as exc:
            logger.warning("Invalid JSON from Product API for %s %s", method, path)
            raise ProductApiResponseError(
                "The product service returned invalid JSON."
            ) from exc

    @staticmethod
    def _extract_error_message(response: httpx.Response, *, default: str) -> str:
        try:
            payload = response.json()
        except ValueError:
            return default
        if isinstance(payload, dict):
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                # Official API messages only; never expose raw bodies wholesale.
                return message.strip()
        return default
