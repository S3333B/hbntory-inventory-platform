"""Guard tests: automated suite must not open real network sockets."""

from __future__ import annotations

import socket

import pytest

from product_mcp_server.app.product_api_client import ProductApiClient
from product_mcp_server.tests.fakes import FakeProductApiClient
from product_mcp_server.app.tools import list_products_handler


def test_fake_client_does_not_touch_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Real network access is forbidden in unit tests.")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)

    client = FakeProductApiClient(products=[])
    result = list_products_handler(client)  # type: ignore[arg-type]
    assert result["status"] == "success"


def test_product_api_client_requires_injected_transport_for_safety() -> None:
    """Document that unit tests inject MockTransport or FakeProductApiClient."""

    # Construction alone does not open a connection.
    client = ProductApiClient(base_url="http://127.0.0.1:9", timeout=0.1)
    assert client.base_url == "http://127.0.0.1:9"
    client.close()
