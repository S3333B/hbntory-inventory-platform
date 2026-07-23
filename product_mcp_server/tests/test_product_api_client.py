"""Network-free tests for ProductApiClient."""

from __future__ import annotations

import httpx
import pytest

from product_mcp_server.app.exceptions import (
    InvalidProductArgumentError,
    InvalidProductIdentifierError,
    ProductApiConnectionError,
    ProductApiResponseError,
    ProductApiTimeoutError,
    ProductNotFoundError,
)
from product_mcp_server.app.product_api_client import (
    ProductApiClient,
    validate_product_identifier,
)
from product_mcp_server.tests.fakes import SAMPLE_PRODUCT, SAMPLE_PRODUCT_DETAIL


def make_client(handler) -> ProductApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, timeout=1.0)
    return ProductApiClient(
        base_url="http://product-api.test",
        timeout=1.0,
        http_client=http_client,
    )


class TestValidateProductIdentifier:
    def test_accepts_positive_integer(self) -> None:
        assert validate_product_identifier(1) == "1"

    def test_accepts_sku(self) -> None:
        assert validate_product_identifier("HB-LAP-1001") == "HB-LAP-1001"

    def test_strips_whitespace(self) -> None:
        assert validate_product_identifier("  HB-LAP-1001  ") == "HB-LAP-1001"

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(InvalidProductIdentifierError):
            validate_product_identifier("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(InvalidProductIdentifierError):
            validate_product_identifier("   ")

    def test_rejects_none(self) -> None:
        with pytest.raises(InvalidProductIdentifierError):
            validate_product_identifier(None)

    def test_rejects_zero_and_negative(self) -> None:
        with pytest.raises(InvalidProductIdentifierError):
            validate_product_identifier(0)
        with pytest.raises(InvalidProductIdentifierError):
            validate_product_identifier(-3)

    def test_rejects_path_characters(self) -> None:
        with pytest.raises(InvalidProductIdentifierError):
            validate_product_identifier("../secret")
        with pytest.raises(InvalidProductIdentifierError):
            validate_product_identifier("a/b")
        with pytest.raises(InvalidProductIdentifierError):
            validate_product_identifier("a?b")


class TestListProducts:
    def test_successful_list(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/products"
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "limit": 20,
                    "offset": 0,
                    "results": [SAMPLE_PRODUCT],
                },
            )

        client = make_client(handler)
        result = client.list_products()
        assert result["count"] == 1
        assert result["results"][0]["sku"] == "HB-LAP-1001"
        assert result["results"][0]["id"] == 1
        client.close()

    def test_empty_list_is_valid(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"count": 0, "limit": 20, "offset": 0, "results": []},
            )

        client = make_client(handler)
        result = client.list_products()
        assert result["count"] == 0
        assert result["results"] == []
        client.close()

    def test_forwards_official_query_params(self) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(dict(request.url.params))
            return httpx.Response(
                200,
                json={"count": 0, "limit": 5, "offset": 10, "results": []},
            )

        client = make_client(handler)
        client.list_products(q="laptop", limit=5, offset=10, sort="name")
        assert captured["q"] == "laptop"
        assert captured["limit"] == "5"
        assert captured["offset"] == "10"
        assert captured["sort"] == "name"
        client.close()

    def test_stable_output_shape(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "limit": 1,
                    "offset": 0,
                    "results": [SAMPLE_PRODUCT],
                },
            )

        client = make_client(handler)
        result = client.list_products(limit=1)
        assert set(result.keys()) == {"count", "limit", "offset", "results"}
        assert isinstance(result["results"], list)
        assert "sku" in result["results"][0]
        assert "name" in result["results"][0]
        client.close()

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"q": 12}, "q must be a string"),
            ({"include_discontinued": "yes"}, "must be a boolean"),
            ({"min_price": -1}, "non-negative"),
            ({"max_price": float("inf")}, "finite"),
            ({"min_price": 20, "max_price": 10}, "less than or equal"),
            ({"limit": 0}, "from 1 to 100"),
            ({"limit": 101}, "from 1 to 100"),
            ({"offset": -1}, "non-negative"),
            ({"sort": "price"}, "supported"),
        ],
    )
    def test_rejects_invalid_filters_without_network(
        self,
        kwargs: dict[str, object],
        message: str,
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("network must not be called for invalid filters")

        client = make_client(handler)
        with pytest.raises(InvalidProductArgumentError) as exc_info:
            client.list_products(**kwargs)  # type: ignore[arg-type]
        assert exc_info.value.code == "INVALID_ARGUMENT"
        assert message in exc_info.value.message
        client.close()

    def test_forwards_all_validated_filter_types(self) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(dict(request.url.params))
            return httpx.Response(
                200,
                json={"count": 0, "limit": 100, "offset": 0, "results": []},
            )

        client = make_client(handler)
        client.list_products(
            category="Laptops",
            supplier_id="SUP-HBT-001",
            include_discontinued=True,
            min_price=1,
            max_price=1000.5,
            limit=100,
            sort="-unit_price",
        )
        assert captured == {
            "category": "Laptops",
            "supplier_id": "SUP-HBT-001",
            "include_discontinued": "true",
            "min_price": "1.0",
            "max_price": "1000.5",
            "limit": "100",
            "sort": "-unit_price",
        }
        client.close()


class TestGetProduct:
    def test_get_by_numeric_id(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/products/1"
            return httpx.Response(200, json=SAMPLE_PRODUCT_DETAIL)

        client = make_client(handler)
        product = client.get_product(1)
        assert product["id"] == 1
        assert product["sku"] == "HB-LAP-1001"
        assert "supplier" in product
        client.close()

    def test_get_by_sku(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/products/HB-LAP-1001"
            return httpx.Response(200, json=SAMPLE_PRODUCT_DETAIL)

        client = make_client(handler)
        product = client.get_product("HB-LAP-1001")
        assert product["sku"] == "HB-LAP-1001"
        client.close()

    def test_product_not_found(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                404,
                json={"error": "not_found", "message": "Product not found."},
            )

        client = make_client(handler)
        with pytest.raises(ProductNotFoundError) as exc_info:
            client.get_product(999999)
        assert exc_info.value.code == "PRODUCT_NOT_FOUND"
        client.close()

    def test_empty_identifier_rejected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("network must not be called for empty id")

        client = make_client(handler)
        with pytest.raises(InvalidProductIdentifierError):
            client.get_product("")
        client.close()

    def test_invalid_identifier_rejected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("network must not be called for invalid id")

        client = make_client(handler)
        with pytest.raises(InvalidProductIdentifierError):
            client.get_product("bad/id")
        client.close()


class TestErrorHandling:
    def test_connection_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        client = make_client(handler)
        with pytest.raises(ProductApiConnectionError) as exc_info:
            client.list_products()
        assert exc_info.value.code == "PRODUCT_API_UNAVAILABLE"
        # Must not silently return an empty list.
        client.close()

    def test_timeout(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        client = make_client(handler)
        with pytest.raises(ProductApiTimeoutError) as exc_info:
            client.list_products()
        assert exc_info.value.code == "PRODUCT_API_TIMEOUT"
        client.close()

    def test_unexpected_http_status(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(418, json={"error": "teapot"})

        client = make_client(handler)
        with pytest.raises(ProductApiResponseError) as exc_info:
            client.list_products()
        assert exc_info.value.code == "INVALID_PRODUCT_RESPONSE"
        client.close()

    def test_server_error_maps_to_unavailable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                503,
                json={
                    "error": "supplier_unavailable",
                    "message": "Forced simulation error.",
                },
            )

        client = make_client(handler)
        with pytest.raises(ProductApiConnectionError):
            client.list_products()
        client.close()

    def test_invalid_json(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                content=b"not-json",
                headers={"Content-Type": "application/json"},
            )

        client = make_client(handler)
        with pytest.raises(ProductApiResponseError) as exc_info:
            client.list_products()
        assert "invalid JSON" in exc_info.value.message.lower() or (
            exc_info.value.code == "INVALID_PRODUCT_RESPONSE"
        )
        client.close()

    def test_invalid_list_shape(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"oops": True})

        client = make_client(handler)
        with pytest.raises(ProductApiResponseError):
            client.list_products()
        client.close()

    @pytest.mark.parametrize(
        "payload",
        [
            {"count": 0, "limit": 20, "offset": 0, "results": [{}]},
            {"count": True, "limit": 20, "offset": 0, "results": []},
            {"count": 0, "limit": 101, "offset": 0, "results": []},
            {"count": 0, "limit": 20, "offset": -1, "results": []},
            {"count": 0, "limit": 20, "results": []},
        ],
    )
    def test_rejects_malformed_product_list_payload(
        self,
        payload: dict[str, object],
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        client = make_client(handler)
        with pytest.raises(ProductApiResponseError) as exc_info:
            client.list_products()
        assert exc_info.value.code == "INVALID_PRODUCT_RESPONSE"
        client.close()

    @pytest.mark.parametrize(
        "payload",
        [
            {"id": 1, "sku": "HB-LAP-1001"},
            {"id": True, "sku": "HB-LAP-1001", "name": "Laptop"},
            {"id": 1, "sku": [], "name": "Laptop"},
            {"id": 1, "sku": "HB-LAP-1001", "name": "Laptop", "tags": "tag"},
        ],
    )
    def test_rejects_malformed_product_detail_payload(
        self,
        payload: dict[str, object],
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        client = make_client(handler)
        with pytest.raises(ProductApiResponseError) as exc_info:
            client.get_product(1)
        assert exc_info.value.code == "INVALID_PRODUCT_RESPONSE"
        client.close()

    @pytest.mark.parametrize(
        "base_url",
        [
            "not-a-url",
            "ftp://product-api.test",
            "http://user:password@product-api.test",
            "http://product-api.test?token=secret",
            "http://product-api.test#fragment",
        ],
    )
    def test_rejects_invalid_base_url(self, base_url: str) -> None:
        with pytest.raises(ValueError):
            ProductApiClient(base_url)

    def test_connection_error_does_not_return_empty_list(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down", request=request)

        client = make_client(handler)
        with pytest.raises(ProductApiConnectionError):
            result = client.list_products()
            # If an exception is not raised, fail hard.
            assert result is not None  # pragma: no cover
        client.close()


class TestClientIsReadOnly:
    def test_request_json_rejects_non_get(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("must not call network for non-GET")

        client = make_client(handler)
        with pytest.raises(ProductApiResponseError):
            client._request_json("POST", "/api/v1/products")
        client.close()

    def test_public_surface_has_no_write_methods(self) -> None:
        public_methods = {
            name
            for name in dir(ProductApiClient)
            if not name.startswith("_") and callable(getattr(ProductApiClient, name))
        }
        forbidden = {
            "create",
            "create_product",
            "update",
            "update_product",
            "delete",
            "delete_product",
            "post",
            "put",
            "patch",
        }
        assert public_methods.isdisjoint(forbidden)
