"""Shared fixtures for Product MCP Server tests."""

from __future__ import annotations

import pytest

from product_mcp_server.tests.fakes import FakeProductApiClient, SAMPLE_PRODUCT


@pytest.fixture
def sample_product() -> dict:
    return dict(SAMPLE_PRODUCT)


@pytest.fixture
def fake_client(sample_product: dict) -> FakeProductApiClient:
    return FakeProductApiClient(products=[sample_product])
