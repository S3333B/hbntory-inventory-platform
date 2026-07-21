"""Boundary for validating canonical product identifiers."""

from typing import Protocol


class ProductValidator(Protocol):
    """Interface implemented later by the External Product API client."""

    def exists(self, external_product_id: int) -> bool:
        """Return whether the canonical numeric product exists."""


class KnownProductValidator:
    """Offline validator for explicitly documented product identifiers.

    This is used only by deterministic initialization. It is not an HTTP client.
    """

    def __init__(self, known_product_ids: set[int] | frozenset[int]) -> None:
        self._known_product_ids = frozenset(known_product_ids)

    def exists(self, external_product_id: int) -> bool:
        """Check an identifier against the explicit allow-list."""

        return external_product_id in self._known_product_ids
