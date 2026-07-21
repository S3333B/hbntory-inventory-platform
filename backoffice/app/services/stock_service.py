"""Business rules for changing local stock quantities."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backoffice.app.models import Branch, Stock
from backoffice.app.services.product_validation import ProductValidator


class StockValidationError(ValueError):
    """Base class for controlled stock validation failures."""


class InvalidQuantityError(StockValidationError):
    """Raised when an adjustment is not a strictly positive integer."""


class BranchNotFoundError(StockValidationError):
    """Raised when the requested branch does not exist."""


class InvalidProductError(StockValidationError):
    """Raised when an external product identifier is structurally invalid."""


class ProductNotFoundError(StockValidationError):
    """Raised when the injected validator does not recognize a product."""


class StockNotFoundError(StockValidationError):
    """Raised when no stock row exists for a removal."""


class InsufficientStockError(StockValidationError):
    """Raised when a removal would make stock negative."""


class StockService:
    """Apply stock rules without coupling models to external HTTP calls."""

    def __init__(self, session: Session, product_validator: ProductValidator) -> None:
        self._session = session
        self._product_validator = product_validator

    def add(self, branch_id: int, external_product_id: int, amount: int) -> Stock:
        """Add a strictly positive amount to a validated branch/product pair."""

        self._validate_amount(amount)
        branch = self._get_branch(branch_id)
        self._validate_product(external_product_id)
        stock = self._find_stock(branch.id, external_product_id, for_update=True)
        if stock is None:
            stock = Stock(
                branch_id=branch.id,
                external_product_id=external_product_id,
                quantity=0,
            )
            self._session.add(stock)
        stock.quantity += amount
        self._session.flush()
        return stock

    def remove(self, branch_id: int, external_product_id: int, amount: int) -> Stock:
        """Remove stock without allowing the resulting quantity to be negative."""

        self._validate_amount(amount)
        branch = self._get_branch(branch_id)
        self._validate_product(external_product_id)
        stock = self._find_stock(branch.id, external_product_id, for_update=True)
        if stock is None:
            raise StockNotFoundError("No stock exists for this branch and product.")
        if amount > stock.quantity:
            raise InsufficientStockError("The removal exceeds the available stock.")
        stock.quantity -= amount
        self._session.flush()
        return stock

    @staticmethod
    def _validate_amount(amount: int) -> None:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise InvalidQuantityError(
                "Stock adjustments must use a strictly positive integer."
            )

    def _get_branch(self, branch_id: int) -> Branch:
        if isinstance(branch_id, bool) or not isinstance(branch_id, int):
            raise BranchNotFoundError("The branch does not exist.")
        branch = self._session.get(Branch, branch_id)
        if branch is None:
            raise BranchNotFoundError("The branch does not exist.")
        return branch

    def _validate_product(self, external_product_id: int) -> None:
        if (
            isinstance(external_product_id, bool)
            or not isinstance(external_product_id, int)
            or external_product_id <= 0
        ):
            raise InvalidProductError(
                "The external product identifier must be a positive integer."
            )
        if not self._product_validator.exists(external_product_id):
            raise ProductNotFoundError("The external product does not exist.")

    def _find_stock(
        self,
        branch_id: int,
        external_product_id: int,
        *,
        for_update: bool,
    ) -> Stock | None:
        statement = select(Stock).where(
            Stock.branch_id == branch_id,
            Stock.external_product_id == external_product_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return self._session.scalar(statement)
