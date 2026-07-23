"""Role and branch authorization tests for protected backend routes."""

from flask.testing import FlaskClient

from backoffice.tests.auth_helpers import login


def test_admin_can_access_user_management(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    login(client, username="admin", password="test-only-admin-password")
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert b"Administrator authorization granted." in response.data


def test_common_cannot_manage_users(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    login(
        client,
        username="common-user",
        password="test-only-common-password",
    )
    response = client.get("/admin/users")
    assert response.status_code == 403


def test_common_can_access_own_branch_stock(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    login(
        client,
        username="common-user",
        password="test-only-common-password",
    )
    response = client.get(f"/stock/branches/{auth_users['branch_id']}")
    assert response.status_code == 200
    assert b"Stock authorization granted" in response.data


def test_common_cannot_access_another_branch_stock(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    login(
        client,
        username="common-user",
        password="test-only-common-password",
    )
    other_branch_id = int(auth_users["branch_id"]) + 1
    response = client.get(f"/stock/branches/{other_branch_id}")
    assert response.status_code == 403


def test_admin_cannot_access_stock_operations(
    client: FlaskClient,
    auth_users: dict[str, object],
) -> None:
    login(client, username="admin", password="test-only-admin-password")
    response = client.get(f"/stock/branches/{auth_users['branch_id']}")
    assert response.status_code == 403


def test_anonymous_user_cannot_access_role_routes(client: FlaskClient) -> None:
    assert client.get("/admin/users").status_code == 302
    assert client.get("/stock/branches/1").status_code == 302
