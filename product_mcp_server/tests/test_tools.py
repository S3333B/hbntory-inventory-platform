"""Network-free tests for MCP product tool handlers and registration."""

from __future__ import annotations

import asyncio

import pytest
from mcp.server.fastmcp import FastMCP

from product_mcp_server.app.config import Settings
from product_mcp_server.app.exceptions import (
    ProductApiConnectionError,
    ProductApiTimeoutError,
)
from product_mcp_server.app.server import create_mcp_server
from product_mcp_server.app.tools import (
    get_product_details_handler,
    list_products_handler,
    register_product_tools,
    registered_write_tools,
)
from product_mcp_server.tests.fakes import FakeProductApiClient, SAMPLE_PRODUCT


class TestListProductsTool:
    def test_successful_list(self, fake_client: FakeProductApiClient) -> None:
        result = list_products_handler(fake_client)  # type: ignore[arg-type]
        assert result["status"] == "success"
        assert result["data"]["count"] == 1
        assert result["data"]["results"][0]["sku"] == "HB-LAP-1001"
        assert fake_client.list_calls

    def test_empty_list(self) -> None:
        client = FakeProductApiClient(products=[])
        result = list_products_handler(client)  # type: ignore[arg-type]
        assert result["status"] == "success"
        assert result["data"]["results"] == []
        assert result["data"]["count"] == 0

    def test_api_unavailable(self) -> None:
        client = FakeProductApiClient(
            list_error=ProductApiConnectionError(),
        )
        result = list_products_handler(client)  # type: ignore[arg-type]
        assert result["status"] == "error"
        assert result["error"]["code"] == "PRODUCT_API_UNAVAILABLE"
        assert "unavailable" in result["error"]["message"].lower()

    def test_timeout(self) -> None:
        client = FakeProductApiClient(list_error=ProductApiTimeoutError())
        result = list_products_handler(client)  # type: ignore[arg-type]
        assert result["status"] == "error"
        assert result["error"]["code"] == "PRODUCT_API_TIMEOUT"

    def test_forwards_filters(self, fake_client: FakeProductApiClient) -> None:
        list_products_handler(
            fake_client,  # type: ignore[arg-type]
            q="laptop",
            limit=5,
            offset=0,
        )
        assert fake_client.list_calls[0]["q"] == "laptop"
        assert fake_client.list_calls[0]["limit"] == 5


class TestGetProductDetailsTool:
    def test_successful_detail(self, fake_client: FakeProductApiClient) -> None:
        result = get_product_details_handler(
            fake_client,  # type: ignore[arg-type]
            id_or_sku=1,
        )
        assert result["status"] == "success"
        assert result["data"]["id"] == 1
        assert result["data"]["sku"] == "HB-LAP-1001"

    def test_get_by_sku(self, fake_client: FakeProductApiClient) -> None:
        result = get_product_details_handler(
            fake_client,  # type: ignore[arg-type]
            id_or_sku="HB-LAP-1001",
        )
        assert result["status"] == "success"
        assert result["data"]["sku"] == "HB-LAP-1001"

    def test_not_found(self) -> None:
        client = FakeProductApiClient(products=[])
        result = get_product_details_handler(
            client,  # type: ignore[arg-type]
            id_or_sku=999999,
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "PRODUCT_NOT_FOUND"

    def test_empty_identifier(self, fake_client: FakeProductApiClient) -> None:
        result = get_product_details_handler(
            fake_client,  # type: ignore[arg-type]
            id_or_sku="",
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "INVALID_PRODUCT_REFERENCE"

    def test_invalid_identifier(self, fake_client: FakeProductApiClient) -> None:
        result = get_product_details_handler(
            fake_client,  # type: ignore[arg-type]
            id_or_sku="a/b",
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "INVALID_PRODUCT_REFERENCE"

    def test_api_unavailable(self) -> None:
        client = FakeProductApiClient(
            products=[SAMPLE_PRODUCT],
            get_error=ProductApiConnectionError(),
        )
        result = get_product_details_handler(
            client,  # type: ignore[arg-type]
            id_or_sku=1,
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "PRODUCT_API_UNAVAILABLE"

    def test_timeout(self) -> None:
        client = FakeProductApiClient(
            get_error=ProductApiTimeoutError(),
        )
        result = get_product_details_handler(
            client,  # type: ignore[arg-type]
            id_or_sku=1,
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "PRODUCT_API_TIMEOUT"

    def test_does_not_invent_product(self) -> None:
        client = FakeProductApiClient(products=[])
        result = get_product_details_handler(
            client,  # type: ignore[arg-type]
            id_or_sku=42,
        )
        assert result["status"] == "error"
        assert "data" not in result or result.get("data") is None


class TestMcpRegistration:
    def test_registers_only_read_tools(self) -> None:
        mcp = FastMCP("test-product-mcp")
        client = FakeProductApiClient()
        names = register_product_tools(mcp, client)  # type: ignore[arg-type]
        assert names == ["list_products", "get_product_details"]
        assert registered_write_tools() == []

        tools = asyncio.run(mcp.list_tools())
        tool_names = sorted(tool.name for tool in tools)
        assert tool_names == ["get_product_details", "list_products"]
        # No write-oriented tools.
        for name in tool_names:
            assert not any(
                verb in name.lower()
                for verb in ("create", "update", "delete", "write", "set")
            )

    def test_create_mcp_server_registers_tools(self) -> None:
        settings = Settings(
            product_api_url="http://product-api.test",
            product_api_timeout=1.0,
            mcp_host="127.0.0.1",
            mcp_port=8001,
            mcp_transport="streamable-http",
            log_level="INFO",
        )
        client = FakeProductApiClient()
        mcp, bound_client = create_mcp_server(settings, client=client)  # type: ignore[arg-type]
        assert bound_client is client
        tools = asyncio.run(mcp.list_tools())
        assert {tool.name for tool in tools} == {
            "list_products",
            "get_product_details",
        }

    def test_call_tool_list_products_via_fastmcp(self) -> None:
        mcp = FastMCP("test-product-mcp")
        client = FakeProductApiClient(products=[SAMPLE_PRODUCT])
        register_product_tools(mcp, client)  # type: ignore[arg-type]

        result = asyncio.run(mcp.call_tool("list_products", {"limit": 1}))
        # FastMCP returns a sequence of content parts and/or a structured result.
        assert result is not None
        # Prefer structured content when available.
        if isinstance(result, tuple):
            content, structured = result
            payload = structured if structured is not None else None
            if payload is None and content:
                # Fall back to text JSON if structured content is absent.
                import json

                text = getattr(content[0], "text", None)
                payload = json.loads(text) if text else None
            assert payload is not None
            assert payload["status"] == "success"
            assert payload["data"]["results"][0]["sku"] == "HB-LAP-1001"
        else:
            raise AssertionError(f"Unexpected call_tool result type: {type(result)}")

    def test_call_tool_get_product_details_via_fastmcp(self) -> None:
        mcp = FastMCP("test-product-mcp")
        client = FakeProductApiClient(products=[SAMPLE_PRODUCT])
        register_product_tools(mcp, client)  # type: ignore[arg-type]

        result = asyncio.run(
            mcp.call_tool("get_product_details", {"id_or_sku": "HB-LAP-1001"})
        )
        assert isinstance(result, tuple)
        content, structured = result
        payload = structured
        if payload is None and content:
            import json

            payload = json.loads(content[0].text)
        assert payload["status"] == "success"
        assert payload["data"]["id"] == 1

    def test_error_propagation_via_fastmcp(self) -> None:
        mcp = FastMCP("test-product-mcp")
        client = FakeProductApiClient(products=[])
        register_product_tools(mcp, client)  # type: ignore[arg-type]

        result = asyncio.run(
            mcp.call_tool("get_product_details", {"id_or_sku": "missing-sku"})
        )
        assert isinstance(result, tuple)
        content, structured = result
        payload = structured
        if payload is None and content:
            import json

            payload = json.loads(content[0].text)
        assert payload["status"] == "error"
        assert payload["error"]["code"] == "PRODUCT_NOT_FOUND"
        # No Python traceback fields.
        assert "traceback" not in str(payload).lower()


class TestConfig:
    def test_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRODUCT_API_URL", "http://example:5000/")
        monkeypatch.setenv("PRODUCT_API_TIMEOUT", "2.5")
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("MCP_PORT", "9001")
        monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
        settings = Settings.from_env()
        assert settings.product_api_url == "http://example:5000"
        assert settings.product_api_timeout == 2.5
        assert settings.mcp_port == 9001

    def test_rejects_invalid_transport(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_TRANSPORT", "websocket")
        with pytest.raises(ValueError):
            Settings.from_env()
