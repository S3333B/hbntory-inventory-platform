"""Business and transport exceptions for the Product API client."""


class ProductApiError(Exception):
    """Base error for Product API client failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidProductIdentifierError(ProductApiError):
    """Raised when a product id or SKU is empty or structurally invalid."""

    def __init__(self, message: str = "The product identifier is invalid.") -> None:
        super().__init__(message, code="INVALID_PRODUCT_REFERENCE")


class InvalidProductArgumentError(ProductApiError):
    """Raised when a Product API list filter is invalid."""

    def __init__(self, message: str = "A product list argument is invalid.") -> None:
        super().__init__(message, code="INVALID_ARGUMENT")


class ProductNotFoundError(ProductApiError):
    """Raised when the external Product API returns HTTP 404 for a product."""

    def __init__(self, message: str = "Product not found.") -> None:
        super().__init__(message, code="PRODUCT_NOT_FOUND")


class ProductApiConnectionError(ProductApiError):
    """Raised when the external Product API cannot be reached."""

    def __init__(
        self,
        message: str = "Product information is temporarily unavailable.",
    ) -> None:
        super().__init__(message, code="PRODUCT_API_UNAVAILABLE")


class ProductApiTimeoutError(ProductApiError):
    """Raised when the external Product API call exceeds the configured timeout."""

    def __init__(
        self,
        message: str = "The product service did not respond in time.",
    ) -> None:
        super().__init__(message, code="PRODUCT_API_TIMEOUT")


class ProductApiResponseError(ProductApiError):
    """Raised for unexpected HTTP status codes or invalid JSON payloads."""

    def __init__(
        self,
        message: str = "The product service returned an unexpected response.",
        *,
        code: str = "INVALID_PRODUCT_RESPONSE",
    ) -> None:
        super().__init__(message, code=code)
