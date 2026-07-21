"""Network-free test doubles."""


class FakeProductValidator:
    """Record calls and validate against an in-memory identifier set."""

    def __init__(self, product_ids: set[int] | None = None) -> None:
        self.product_ids = {1} if product_ids is None else product_ids
        self.calls: list[int] = []

    def exists(self, external_product_id: int) -> bool:
        self.calls.append(external_product_id)
        return external_product_id in self.product_ids
