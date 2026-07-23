"""Shared isolated database fixtures."""

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backoffice.app import create_app
from backoffice.app.database import (
    create_engine_from_url,
    create_schema,
    make_session_factory,
)
from backoffice.app.models import Branch, User, UserRole
from backoffice.tests.fakes import FakeProductValidator


@pytest.fixture
def engine() -> Engine:
    database_engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    create_schema(database_engine)
    yield database_engine
    database_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return make_session_factory(engine)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Session:
    database_session = session_factory()
    yield database_session
    database_session.rollback()
    database_session.close()


@pytest.fixture
def product_validator() -> FakeProductValidator:
    return FakeProductValidator({1})


@pytest.fixture(scope="session")
def app(tmp_path_factory: pytest.TempPathFactory) -> Flask:
    database_path = tmp_path_factory.mktemp("backoffice-auth") / "test.db"
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-session-secret",
            "DATABASE_URL": f"sqlite+pysqlite:///{database_path}",
            "SESSION_COOKIE_SECURE": False,
            "WTF_CSRF_ENABLED": True,
        }
    )
    create_schema(application.extensions["hbntory_engine"])
    yield application
    application.extensions["hbntory_engine"].dispose()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture(scope="session")
def auth_users(app: Flask) -> dict[str, object]:
    factory = app.extensions["hbntory_session_factory"]
    with factory.begin() as database_session:
        branch = Branch(name="Lille")
        database_session.add(branch)
        database_session.flush()

        admin = User(username="admin", role=UserRole.ADMIN, branch_id=None)
        admin.set_password("test-only-admin-password")
        common = User(
            username="common-user",
            role=UserRole.COMMON,
            branch_id=branch.id,
        )
        common.set_password("test-only-common-password")
        deleted = User(
            username="deleted-user",
            role=UserRole.COMMON,
            branch_id=branch.id,
        )
        deleted.set_password("test-only-deleted-password")
        deleted.soft_delete()
        database_session.add_all([admin, common, deleted])
        database_session.flush()

        result = {
            "branch_id": branch.id,
            "admin_id": admin.id,
            "common_id": common.id,
            "deleted_id": deleted.id,
        }
    return result
