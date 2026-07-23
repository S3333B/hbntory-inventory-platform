"""Backoffice login, logout, and session tests."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from backoffice.app.authentication import (
    GENERIC_LOGIN_ERROR,
    safe_next_url,
    verify_password,
)
from backoffice.app.models import User
from backoffice.tests.auth_helpers import csrf_token, login, logout


def test_login_page_contains_minimal_secure_form(client: FlaskClient) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert b'name="username"' in response.data
    assert b'name="password"' in response.data
    assert b'name="csrf_token"' in response.data


def test_admin_login_creates_session(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    response = login(
        client,
        username="admin",
        password="test-only-admin-password",
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    with client.session_transaction() as browser_session:
        assert browser_session["_user_id"] == str(auth_users["admin_id"])
        assert "password" not in browser_session
        assert "password_hash" not in browser_session


def test_authenticated_cookie_has_secure_browser_attributes(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    response = login(
        client,
        username="admin",
        password="test-only-admin-password",
    )
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_active_common_user_can_login(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    response = login(
        client,
        username="common-user",
        password="test-only-common-password",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Authentication is active." in response.data
    assert b"common-user" in response.data


def test_unknown_user_and_wrong_password_have_identical_public_error(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    unknown = login(
        client,
        username="unknown-user",
        password="test-only-wrong-password",
    )
    wrong_password = login(
        client,
        username="admin",
        password="test-only-wrong-password",
    )
    assert unknown.status_code == wrong_password.status_code == 401
    assert GENERIC_LOGIN_ERROR.encode() in unknown.data
    assert GENERIC_LOGIN_ERROR.encode() in wrong_password.data


def test_deleted_user_is_refused_with_generic_error(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    response = login(
        client,
        username="deleted-user",
        password="test-only-deleted-password",
    )
    assert response.status_code == 401
    assert GENERIC_LOGIN_ERROR.encode() in response.data


def test_missing_password_is_refused(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    token = csrf_token(client, "/login")
    response = client.post(
        "/login",
        data={"csrf_token": token, "username": "admin", "password": ""},
    )
    assert response.status_code == 401
    assert GENERIC_LOGIN_ERROR.encode() in response.data


def test_missing_csrf_token_is_refused(client: FlaskClient) -> None:
    response = client.post(
        "/login",
        data={"username": "admin", "password": "test-only-admin-password"},
    )
    assert response.status_code == 400
    assert b"Invalid request" in response.data


def test_logout_clears_authenticated_session(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    login(
        client,
        username="admin",
        password="test-only-admin-password",
    )
    response = logout(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as browser_session:
        assert "_user_id" not in browser_session


def test_logout_is_not_available_through_get(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    login(
        client,
        username="admin",
        password="test-only-admin-password",
    )
    assert client.get("/logout").status_code == 405


def test_protected_route_redirects_anonymous_user(client: FlaskClient) -> None:
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login?next=%2Fdashboard" in response.headers["Location"]


def test_protected_route_accepts_authenticated_user(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    login(
        client,
        username="admin",
        password="test-only-admin-password",
    )
    assert client.get("/dashboard").status_code == 200


def test_soft_delete_after_login_revokes_session_access(
    app: Flask,
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    login(
        client,
        username="common-user",
        password="test-only-common-password",
    )
    factory = app.extensions["hbntory_session_factory"]
    with factory.begin() as database_session:
        user = database_session.get(User, auth_users["common_id"])
        assert user is not None
        user.soft_delete()

    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    with factory.begin() as database_session:
        user = database_session.get(User, auth_users["common_id"])
        assert user is not None
        user.deleted_at = None


def test_password_hash_is_never_clear_text(
    app: Flask,
    auth_users: dict[str, object],
) -> None:
    factory = app.extensions["hbntory_session_factory"]
    with factory() as database_session:
        user = database_session.get(User, auth_users["admin_id"])
        assert user is not None
        assert user.password_hash != "test-only-admin-password"
        assert "test-only-admin-password" not in user.password_hash
        assert verify_password(user.password_hash, "test-only-admin-password")
        assert not verify_password(user.password_hash, "wrong-password")


def test_sensitive_values_do_not_appear_in_authentication_response(
    app: Flask,
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    candidate = "response-must-not-contain-this-password"
    response = login(client, username="admin", password=candidate)
    factory = app.extensions["hbntory_session_factory"]
    with factory() as database_session:
        user = database_session.get(User, auth_users["admin_id"])
        assert user is not None
        assert candidate.encode() not in response.data
        assert user.password_hash.encode() not in response.data
        assert app.secret_key.encode() not in response.data


def test_next_url_accepts_only_local_paths() -> None:
    assert safe_next_url("/admin/users") == "/admin/users"
    assert safe_next_url("https://evil.example/steal") is None
    assert safe_next_url("//evil.example/steal") is None
    assert safe_next_url(r"/\evil") is None


def test_login_rejects_external_next_redirect(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    response = login(
        client,
        username="admin",
        password="test-only-admin-password",
        next_url="https://evil.example/steal",
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert "evil.example" not in response.headers["Location"]


def test_login_accepts_safe_local_next_redirect(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    response = login(
        client,
        username="admin",
        password="test-only-admin-password",
        next_url="/admin/users",
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")
