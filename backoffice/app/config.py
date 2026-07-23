"""Environment-backed Backoffice configuration."""

from __future__ import annotations

import os
import secrets
from typing import Any


def _read_boolean(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean value.")


def build_config(test_config: dict[str, object] | None = None) -> dict[str, Any]:
    """Build Flask settings, requiring secrets outside test mode."""

    overrides = dict(test_config or {})
    testing = bool(overrides.get("TESTING", False))

    secret_key = overrides.get("SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not secret_key and testing:
        secret_key = secrets.token_urlsafe(32)
    if not isinstance(secret_key, str) or not secret_key:
        raise RuntimeError("SECRET_KEY is required outside tests.")

    database_url = overrides.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not isinstance(database_url, str) or not database_url.strip():
        raise RuntimeError("DATABASE_URL is required.")

    secure_cookie = overrides.get("SESSION_COOKIE_SECURE")
    if secure_cookie is None:
        secure_cookie = _read_boolean("SESSION_COOKIE_SECURE", False)
    if not isinstance(secure_cookie, bool):
        raise RuntimeError("SESSION_COOKIE_SECURE must be a boolean value.")

    config: dict[str, Any] = {
        "DATABASE_URL": database_url.strip(),
        "SECRET_KEY": secret_key,
        "TESTING": testing,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": secure_cookie,
        "WTF_CSRF_ENABLED": True,
        "WTF_CSRF_TIME_LIMIT": 3600,
    }
    config.update(overrides)
    return config
