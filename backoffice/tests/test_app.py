"""Application factory and security configuration tests."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from flask import Flask

from backoffice.app import create_app
from backoffice.app.database import create_schema


def test_create_app_with_isolated_test_configuration(app: Flask) -> None:
    assert app.testing is True
    assert app.config["DATABASE_URL"].startswith("sqlite+pysqlite:///")
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is False
    assert "hbntory_session_factory" in app.extensions


def test_test_app_can_generate_ephemeral_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    application = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'ephemeral.db'}",
        }
    )
    try:
        assert isinstance(application.secret_key, str)
        assert application.secret_key
    finally:
        application.extensions["hbntory_engine"].dispose()


def test_missing_secret_key_fails_outside_tests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(
            {
                "TESTING": False,
                "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'missing.db'}",
            }
        )


def test_secure_cookie_setting_comes_from_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'secure.db'}",
        }
    )
    try:
        assert application.config["SESSION_COOKIE_SECURE"] is True
    finally:
        application.extensions["hbntory_engine"].dispose()


def test_authentication_does_not_require_external_product_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Authentication must not use the network.")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'offline.db'}",
        }
    )
    try:
        create_schema(application.extensions["hbntory_engine"])
        assert application.test_client().get("/login").status_code == 200
    finally:
        application.extensions["hbntory_engine"].dispose()
