"""Explicit exceptions for read-only stock queries."""


class StockQueryError(Exception):
    """Base error for controlled stock query failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidStockArgumentError(StockQueryError):
    """Raised when a stock tool argument is structurally invalid."""

    def __init__(self, message: str = "A stock query argument is invalid.") -> None:
        super().__init__(message, code="INVALID_ARGUMENT")


class BranchNotFoundError(StockQueryError):
    """Raised when the requested branch does not exist."""

    def __init__(self, message: str = "The branch was not found.") -> None:
        super().__init__(message, code="BRANCH_NOT_FOUND")


class StockNotFoundError(StockQueryError):
    """Raised when no positive stock exists for a requested product."""

    def __init__(
        self,
        message: str = "No available stock was found for this product.",
    ) -> None:
        super().__init__(message, code="STOCK_NOT_FOUND")


class DatabaseUnavailableError(StockQueryError):
    """Raised when PostgreSQL (or the test database) cannot be reached."""

    def __init__(
        self,
        message: str = "Stock information is temporarily unavailable.",
    ) -> None:
        super().__init__(message, code="DATABASE_UNAVAILABLE")


class InvalidStockResponseError(StockQueryError):
    """Raised when the repository returns an unexpected internal shape."""

    def __init__(
        self,
        message: str = "Stock information could not be interpreted safely.",
    ) -> None:
        super().__init__(message, code="INVALID_STOCK_RESPONSE")
