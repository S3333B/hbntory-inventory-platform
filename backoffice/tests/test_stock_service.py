"""Stock business-rule tests."""

import pytest
from sqlalchemy.orm import Session

from backoffice.app.models import Branch, Stock
from backoffice.app.services.stock_service import (
    BranchNotFoundError,
    InsufficientStockError,
    InvalidProductError,
    InvalidQuantityError,
    ProductNotFoundError,
    StockService,
)
from backoffice.tests.fakes import FakeProductValidator


def make_service(
    session: Session,
    product_validator: FakeProductValidator,
) -> tuple[Branch, StockService]:
    branch = Branch(name="Lille")
    session.add(branch)
    session.commit()
    return branch, StockService(session, product_validator)


def test_add_positive_quantity(
    session: Session,
    product_validator: FakeProductValidator,
) -> None:
    branch, service = make_service(session, product_validator)

    stock = service.add(branch.id, 1, 5)
    session.commit()

    assert stock.quantity == 5
    assert product_validator.calls == [1]


@pytest.mark.parametrize("amount", [0, -1, True, 1.5, "2", None])
def test_add_rejects_non_positive_integer_amounts(
    session: Session,
    product_validator: FakeProductValidator,
    amount: object,
) -> None:
    branch, service = make_service(session, product_validator)

    with pytest.raises(InvalidQuantityError):
        service.add(branch.id, 1, amount)  # type: ignore[arg-type]


def test_remove_valid_quantity(
    session: Session,
    product_validator: FakeProductValidator,
) -> None:
    branch, service = make_service(session, product_validator)
    stock = Stock(branch_id=branch.id, external_product_id=1, quantity=5)
    session.add(stock)
    session.commit()

    result = service.remove(branch.id, 1, 3)
    session.commit()

    assert result.quantity == 2


def test_remove_more_than_available_is_rejected(
    session: Session,
    product_validator: FakeProductValidator,
) -> None:
    branch, service = make_service(session, product_validator)
    session.add(Stock(branch_id=branch.id, external_product_id=1, quantity=2))
    session.commit()

    with pytest.raises(InsufficientStockError):
        service.remove(branch.id, 1, 3)


def test_nonexistent_branch_is_rejected(
    session: Session,
    product_validator: FakeProductValidator,
) -> None:
    service = StockService(session, product_validator)

    with pytest.raises(BranchNotFoundError):
        service.add(999, 1, 1)


@pytest.mark.parametrize("external_product_id", [None, "", 0, -1, True])
def test_invalid_external_product_identifier_is_rejected(
    session: Session,
    product_validator: FakeProductValidator,
    external_product_id: object,
) -> None:
    branch, service = make_service(session, product_validator)

    with pytest.raises(InvalidProductError):
        service.add(branch.id, external_product_id, 1)  # type: ignore[arg-type]


def test_unknown_external_product_is_rejected(session: Session) -> None:
    validator = FakeProductValidator(set())
    branch, service = make_service(session, validator)

    with pytest.raises(ProductNotFoundError):
        service.add(branch.id, 999, 1)
