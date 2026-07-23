"""In-process checks for the MCP Streamable HTTP endpoint.

The ASGI transport keeps these tests deterministic: no socket is opened and
the official External Product API is replaced by the injectable fake client.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from mcp.shared.version import LATEST_PROTOCOL_VERSION

from product_mcp_server.app.config import Settings
from product_mcp_server.app.server import create_mcp_server
from product_mcp_server.tests.fakes import FakeProductApiClient

MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def mcp_request(
    method: str,
    *,
    request_id: int,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one JSON-RPC request for the in-process MCP endpoint."""

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }


async def exercise_streamable_http() -> None:
    settings = Settings(
        product_api_url="http://product-api.test",
        product_api_timeout=1.0,
        mcp_host="127.0.0.1",
        mcp_port=8001,
        mcp_transport="streamable-http",
        log_level="INFO",
    )
    mcp, _ = create_mcp_server(settings, client=FakeProductApiClient())
    transport = httpx.ASGITransport(app=mcp.streamable_http_app())

    async with mcp.session_manager.run():
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:8001",
        ) as client:
            health = await client.get("/health")
            assert health.status_code == 200
            assert health.json()["read_only"] is True

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
                            "name": "hbntory-test-client",
                            "version": "1.0",
                        },
                    },
                ),
            )
            assert initialized.status_code == 200
            assert initialized.json()["result"]["serverInfo"]["name"] == (
                "hbntory-product-mcp"
            )

            listed = await client.post(
                "/mcp",
                headers=MCP_HEADERS,
                json=mcp_request("tools/list", request_id=2),
            )
            assert listed.status_code == 200
            tool_names = {tool["name"] for tool in listed.json()["result"]["tools"]}
            assert tool_names == {"list_products", "get_product_details"}

            called = await client.post(
                "/mcp",
                headers=MCP_HEADERS,
                json=mcp_request(
                    "tools/call",
                    request_id=3,
                    params={
                        "name": "get_product_details",
                        "arguments": {"id_or_sku": 1},
                    },
                ),
            )
            assert called.status_code == 200
            result = called.json()["result"]
            assert result["isError"] is False
            assert result["structuredContent"]["status"] == "success"
            assert result["structuredContent"]["data"]["id"] == 1


def test_streamable_http_protocol_without_network() -> None:
    asyncio.run(exercise_streamable_http())
