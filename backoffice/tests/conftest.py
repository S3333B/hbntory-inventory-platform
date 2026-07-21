"""Shared isolated database fixtures."""

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backoffice.app.database import (
    create_engine_from_url,
    create_schema,
    make_session_factory,
)
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
