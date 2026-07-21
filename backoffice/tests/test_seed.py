"""Initial database creation and seed tests."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from werkzeug.security import check_password_hash

from backoffice.app.models import Branch, Stock, User
from backoffice.app.seed import InitializationError, initialize_database, initialize_data
from backoffice.tests.fakes import FakeProductValidator


def test_initialization_creates_expected_data_and_is_idempotent(
    engine: Engine,
    session_factory: sessionmaker[Session],
) -> None:
    clear_password = "test-only-initial-password"
    validator = FakeProductValidator({1})

    first = initialize_database(
        engine,
        admin_password=clear_password,
        product_validator=validator,
        session_factory=session_factory,
    )
    second = initialize_database(
        engine,
        admin_password=clear_password,
        product_validator=validator,
        session_factory=session_factory,
    )

    with session_factory() as session:
        admin = session.scalar(select(User).where(User.username == "admin"))
        assert admin is not None
        assert admin.branch_id is None
        assert admin.password_hash != clear_password
        assert clear_password not in admin.password_hash
        assert check_password_hash(admin.password_hash, clear_password)
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(Branch)) == 2
        assert session.scalar(select(func.count()).select_from(Stock)) == 2
        assert set(session.scalars(select(Branch.name))) == {"Lille", "Roubaix"}
        assert set(session.scalars(select(Stock.external_product_id))) == {1}

    assert first == second


def test_initialization_requires_admin_password(session: Session) -> None:
    with pytest.raises(InitializationError, match="INITIAL_ADMIN_PASSWORD"):
        initialize_data(
            session,
            admin_password="",
            product_validator=FakeProductValidator({1}),
        )


def test_initialization_rejects_unvalidated_seed_product(session: Session) -> None:
    with pytest.raises(InitializationError, match="product 1"):
        initialize_data(
            session,
            admin_password="test-only-initial-password",
            product_validator=FakeProductValidator(set()),
        )
