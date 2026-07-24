"""Isolated SQLite tests for the read-only SQLAlchemy stock repository."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from backoffice.app.database import create_engine_from_url, create_schema, make_session_factory
from backoffice.app.models import Branch, Stock
from product_mcp_server.app.stock_exceptions import DatabaseUnavailableError
from product_mcp_server.app.stock_query import (
    check_shopping_list,
    get_branch_stock,
    get_product_stock,
)
from product_mcp_server.app.stock_repository import SqlAlchemyStockRepository


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    create_schema(engine)
    factory = make_session_factory(engine)
    with factory() as session:
        lille = Branch(name="Lille")
        roubaix = Branch(name="Roubaix")
        empty = Branch(name="Empty")
        session.add_all([lille, roubaix, empty])
        session.flush()
        session.add_all(
            [
                Stock(branch_id=lille.id, external_product_id=1, quantity=5),
                Stock(branch_id=roubaix.id, external_product_id=1, quantity=3),
                Stock(branch_id=lille.id, external_product_id=2, quantity=4),
                Stock(branch_id=roubaix.id, external_product_id=2, quantity=0),
            ]
        )
        session.commit()
    yield factory
    engine.dispose()


@pytest.fixture
def repository(session_factory: sessionmaker[Session]) -> SqlAlchemyStockRepository:
    return SqlAlchemyStockRepository(session_factory)


def test_product_stock_across_branches(repository: SqlAlchemyStockRepository) -> None:
    result = get_product_stock(repository, 1)
    assert result["total_quantity"] == 8
    assert len(result["branches"]) == 2


def test_branch_stock_omits_zero_quantity(repository: SqlAlchemyStockRepository) -> None:
    result = get_branch_stock(repository, "Roubaix")
    assert result["stocks"] == [{"external_product_id": 1, "quantity": 3}]


def test_empty_branch_stock(repository: SqlAlchemyStockRepository) -> None:
    result = get_branch_stock(repository, "Empty")
    assert result["stocks"] == []


def test_shopping_list_single_branch(repository: SqlAlchemyStockRepository) -> None:
    result = check_shopping_list(
        repository,
        [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}],
    )
    assert result["single_branch_possible"] is True
    assert result["single_branch_candidates"][0]["branch_name"] == "Lille"


def test_database_unavailable_maps_sqlalchemy_errors() -> None:
    from sqlalchemy.exc import OperationalError

    class BrokenSessionFactory:
        def __call__(self) -> Session:
            raise OperationalError("SELECT 1", {}, Exception("db down"))

    repository = SqlAlchemyStockRepository(BrokenSessionFactory())  # type: ignore[arg-type]
    with pytest.raises(DatabaseUnavailableError):
        repository.list_product_stock(1)
