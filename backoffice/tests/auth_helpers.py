"""Helpers for exercising CSRF-protected authentication forms."""

from __future__ import annotations

import re

from flask.testing import FlaskClient
from werkzeug.test import TestResponse

CSRF_PATTERN = re.compile(rb'name="csrf_token"[^>]*value="([^"]+)"')


def csrf_token(client: FlaskClient, path: str) -> str:
    response = client.get(path)
    match = CSRF_PATTERN.search(response.data)
    if match is None:
        raise AssertionError(f"No CSRF token found at {path}.")
    return match.group(1).decode("utf-8")


def login(
    client: FlaskClient,
    *,
    username: str,
    password: str,
    next_url: str = "",
    follow_redirects: bool = False,
) -> TestResponse:
    token = csrf_token(client, f"/login?next={next_url}" if next_url else "/login")
    return client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": username,
            "password": password,
            "next_url": next_url,
        },
        follow_redirects=follow_redirects,
    )


def logout(
    client: FlaskClient,
    *,
    follow_redirects: bool = False,
) -> TestResponse:
    token = csrf_token(client, "/dashboard")
    return client.post(
        "/logout",
        data={"csrf_token": token},
        follow_redirects=follow_redirects,
    )
