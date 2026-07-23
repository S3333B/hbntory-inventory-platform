"""Regression tests for Product API port resolution in Docker Compose."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def render_compose_config(
    tmp_path: Path,
    *,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Render Compose without reading a developer's local .env file."""

    if shutil.which("docker") is None:
        pytest.skip("Docker CLI is not installed.")

    empty_env_file = tmp_path / "empty.env"
    empty_env_file.write_text("", encoding="utf-8")

    command_environment = os.environ.copy()
    command_environment.pop("HBN_PRODUCTS_PORT", None)
    command_environment.pop("PRODUCT_API_URL_DOCKER", None)
    command_environment.update(environment or {})

    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(empty_env_file),
            "config",
            "--format",
            "json",
        ],
        cwd=REPOSITORY_ROOT,
        env=command_environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def assert_product_api_container_port(
    config: dict[str, Any],
    *,
    expected_port: int,
) -> None:
    product_api = config["services"]["external-products-api"]
    assert product_api["environment"]["HBN_PRODUCTS_PORT"] == str(expected_port)
    assert product_api["ports"][0]["target"] == expected_port
    health_command = " ".join(product_api["healthcheck"]["test"])
    assert "HBN_PRODUCTS_PORT" in health_command


def test_default_product_api_port_is_shared_with_mcp(tmp_path: Path) -> None:
    config = render_compose_config(tmp_path)

    assert_product_api_container_port(config, expected_port=5000)
    assert (
        config["services"]["product-mcp-server"]["environment"]["PRODUCT_API_URL"]
        == "http://external-products-api:5000"
    )


def test_custom_product_api_port_is_shared_with_mcp(tmp_path: Path) -> None:
    config = render_compose_config(
        tmp_path,
        environment={"HBN_PRODUCTS_PORT": "5100"},
    )

    assert_product_api_container_port(config, expected_port=5100)
    assert (
        config["services"]["product-mcp-server"]["environment"]["PRODUCT_API_URL"]
        == "http://external-products-api:5100"
    )


def test_explicit_mcp_product_api_url_has_priority(tmp_path: Path) -> None:
    explicit_url = "http://catalog.internal:7777"
    config = render_compose_config(
        tmp_path,
        environment={
            "HBN_PRODUCTS_PORT": "5100",
            "PRODUCT_API_URL_DOCKER": explicit_url,
        },
    )

    assert_product_api_container_port(config, expected_port=5100)
    assert (
        config["services"]["product-mcp-server"]["environment"]["PRODUCT_API_URL"]
        == explicit_url
    )
