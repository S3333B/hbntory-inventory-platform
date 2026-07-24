"""MCP registration and protocol tests for read-only stock tools."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.version import LATEST_PROTOCOL_VERSION

from product_mcp_server.app.config import Settings
from product_mcp_server.app.server import create_mcp_server
from product_mcp_server.app.stock_repository import BranchRecord, StockLine
from product_mcp_server.app.stock_tools import register_stock_tools
from product_mcp_server.app.tools import (
    FORBIDDEN_STOCK_WRITE_VERBS,
    register_product_tools,
    registered_write_tools,
)
from product_mcp_server.tests.fakes import FakeProductApiClient, FakeStockRepository

MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def stock_repo() -> FakeStockRepository:
    return FakeStockRepository(
        branches=[
            BranchRecord(1, "Lille"),
            BranchRecord(2, "Roubaix"),
        ],
        lines=[
            StockLine(1, "Lille", 10, 5),
            StockLine(2, "Roubaix", 10, 3),
            StockLine(1, "Lille", 20, 2),
        ],
    )


def extract_payload(result: Any) -> dict[str, Any]:
    assert isinstance(result, tuple)
    content, structured = result
    if structured is not None:
        return structured
    text = getattr(content[0], "text", None)
    assert text is not None
    return json.loads(text)


class TestStockToolRegistration:
    def test_registers_stock_tools_only_read_only(self) -> None:
        mcp = FastMCP("test-stock-mcp")
        names = register_stock_tools(mcp, stock_repo())
        assert names == [
            "get_product_stock",
            "get_branch_stock",
            "check_shopping_list",
        ]
        assert registered_write_tools() == []
        tools = asyncio.run(mcp.list_tools())
        tool_names = sorted(tool.name for tool in tools)
        assert tool_names == [
            "check_shopping_list",
            "get_branch_stock",
            "get_product_stock",
        ]
        by_name = {tool.name: tool for tool in tools}
        product_schema = by_name["get_product_stock"].inputSchema["properties"][
            "product_id"
        ]
        assert product_schema["type"] == "integer"
        branch_schema = by_name["get_branch_stock"].inputSchema["properties"][
            "branch"
        ]
        assert {
            option["type"] for option in branch_schema["anyOf"]
        } == {"integer", "string"}
        items_schema = by_name["check_shopping_list"].inputSchema["properties"][
            "items"
        ]
        assert items_schema["type"] == "array"
        assert items_schema["items"]["type"] == "object"
        for name in tool_names:
            assert name not in FORBIDDEN_STOCK_WRITE_VERBS
            assert not any(
                verb in name.lower()
                for verb in (
                    "create",
                    "update",
                    "delete",
                    "write",
                    "add_stock",
                    "remove",
                    "sql",
                )
            )

    def test_create_mcp_server_registers_product_and_stock_tools(self) -> None:
        settings = Settings(
            product_api_url="http://product-api.test",
            product_api_timeout=1.0,
            mcp_host="127.0.0.1",
            mcp_port=8001,
            mcp_transport="streamable-http",
            log_level="INFO",
            database_url=None,
        )
        mcp, _, repository, _ = create_mcp_server(
            settings,
            client=FakeProductApiClient(),
            stock_repository=stock_repo(),
        )
        assert repository is not None
        tools = asyncio.run(mcp.list_tools())
        assert {tool.name for tool in tools} == {
            "list_products",
            "get_product_details",
            "get_product_stock",
            "get_branch_stock",
            "check_shopping_list",
        }

    def test_call_stock_tools_via_fastmcp(self) -> None:
        mcp = FastMCP("test-stock-mcp")
        register_stock_tools(mcp, stock_repo())

        product = extract_payload(
            asyncio.run(mcp.call_tool("get_product_stock", {"product_id": 10}))
        )
        assert product["status"] == "success"
        assert product["data"]["total_quantity"] == 8

        branch = extract_payload(
            asyncio.run(mcp.call_tool("get_branch_stock", {"branch": "Lille"}))
        )
        assert branch["status"] == "success"
        assert branch["data"]["branch_name"] == "Lille"

        shopping = extract_payload(
            asyncio.run(
                mcp.call_tool(
                    "check_shopping_list",
                    {"items": [{"product_id": 10, "quantity": 2}]},
                )
            )
        )
        assert shopping["status"] == "success"
        assert shopping["data"]["fulfillable"] is True

    def test_fastmcp_does_not_coerce_invalid_stock_arguments(self) -> None:
        mcp = FastMCP("test-stock-validation")
        register_stock_tools(mcp, stock_repo())

        invalid_product = extract_payload(
            asyncio.run(mcp.call_tool("get_product_stock", {"product_id": True}))
        )
        assert invalid_product["error"]["code"] == "INVALID_ARGUMENT"

        invalid_quantity = extract_payload(
            asyncio.run(
                mcp.call_tool(
                    "check_shopping_list",
                    {"items": [{"product_id": 10, "quantity": True}]},
                )
            )
        )
        assert invalid_quantity["error"]["code"] == "INVALID_ARGUMENT"

        invalid_branch = extract_payload(
            asyncio.run(mcp.call_tool("get_branch_stock", {"branch": None}))
        )
        assert invalid_branch["error"]["code"] == "INVALID_ARGUMENT"

    def test_product_tools_still_work_alongside_stock_tools(self) -> None:
        mcp = FastMCP("test-combined-mcp")
        register_product_tools(mcp, FakeProductApiClient())
        register_stock_tools(mcp, stock_repo())
        product = extract_payload(
            asyncio.run(mcp.call_tool("get_product_details", {"id_or_sku": 1}))
        )
        assert product["status"] == "success"
        stock = extract_payload(
            asyncio.run(mcp.call_tool("get_product_stock", {"product_id": 10}))
        )
        assert stock["status"] == "success"

    def test_no_write_or_sql_tools_exposed(self) -> None:
        settings = Settings(
            product_api_url="http://product-api.test",
            product_api_timeout=1.0,
            mcp_host="127.0.0.1",
            mcp_port=8001,
            mcp_transport="streamable-http",
            log_level="INFO",
            database_url=None,
        )
        mcp, _, _, _ = create_mcp_server(
            settings,
            client=FakeProductApiClient(),
            stock_repository=stock_repo(),
        )
        tools = asyncio.run(mcp.list_tools())
        names = {tool.name for tool in tools}
        for forbidden in FORBIDDEN_STOCK_WRITE_VERBS:
            assert forbidden not in names
        assert "execute_sql" not in names
        assert "query" not in names


def mcp_request(
    method: str,
    *,
    request_id: int,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }


async def exercise_streamable_http_with_stock() -> None:
    settings = Settings(
        product_api_url="http://product-api.test",
        product_api_timeout=1.0,
        mcp_host="127.0.0.1",
        mcp_port=8001,
        mcp_transport="streamable-http",
        log_level="INFO",
        database_url=None,
    )
    mcp, _, _, _ = create_mcp_server(
        settings,
        client=FakeProductApiClient(),
        stock_repository=stock_repo(),
    )
    transport = httpx.ASGITransport(app=mcp.streamable_http_app())

    async with mcp.session_manager.run():
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:8001",
        ) as client:
            health = await client.get("/health")
            assert health.status_code == 200
            body = health.json()
            assert body["read_only"] is True
            assert body["stock_tools_enabled"] is True

            initialized = await client.post(
                "/mcp",
                headers=MCP_HEADERS,
                json=mcp_request(
                    "initialize",
                    request_id=1,
                    params={
                        "protocolVersion": LATEST_PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {
                            "name": "hbntory-stock-test-client",
                            "version": "1.0",
                        },
                    },
                ),
            )
            assert initialized.status_code == 200

            listed = await client.post(
                "/mcp",
                headers=MCP_HEADERS,
                json=mcp_request("tools/list", request_id=2),
            )
            assert listed.status_code == 200
            tool_names = {tool["name"] for tool in listed.json()["result"]["tools"]}
            assert tool_names == {
                "list_products",
                "get_product_details",
                "get_product_stock",
                "get_branch_stock",
                "check_shopping_list",
            }

            called = await client.post(
                "/mcp",
                headers=MCP_HEADERS,
                json=mcp_request(
                    "tools/call",
                    request_id=3,
                    params={
                        "name": "get_product_stock",
                        "arguments": {"product_id": 10},
                    },
                ),
            )
            assert called.status_code == 200
            result = called.json()["result"]
            assert result["isError"] is False
            assert result["structuredContent"]["status"] == "success"
            assert result["structuredContent"]["data"]["total_quantity"] == 8

            unknown = await client.post(
                "/mcp",
                headers=MCP_HEADERS,
                json=mcp_request(
                    "tools/call",
                    request_id=4,
                    params={
                        "name": "get_branch_stock",
                        "arguments": {"branch": "Unknown"},
                    },
                ),
            )
            assert unknown.status_code == 200
            unknown_result = unknown.json()["result"]
            assert unknown_result["structuredContent"]["status"] == "error"
            assert (
                unknown_result["structuredContent"]["error"]["code"]
                == "BRANCH_NOT_FOUND"
            )


def test_streamable_http_stock_protocol_without_network() -> None:
    asyncio.run(exercise_streamable_http_with_stock())
