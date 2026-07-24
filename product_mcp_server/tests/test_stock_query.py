"""Unit tests for deterministic read-only stock query logic."""

from __future__ import annotations

import pytest

from product_mcp_server.app.stock_exceptions import (
    BranchNotFoundError,
    DatabaseUnavailableError,
    InvalidStockArgumentError,
    InvalidStockResponseError,
    StockNotFoundError,
)
from product_mcp_server.app.stock_query import (
    check_shopping_list,
    get_branch_stock,
    get_product_stock,
    normalize_shopping_items,
)
from product_mcp_server.app.stock_repository import BranchRecord, StockLine
from product_mcp_server.app.stock_tools import (
    check_shopping_list_handler,
    get_branch_stock_handler,
    get_product_stock_handler,
)
from product_mcp_server.tests.fakes import FakeStockRepository


def sample_repo() -> FakeStockRepository:
    return FakeStockRepository(
        branches=[
            BranchRecord(1, "Lille"),
            BranchRecord(2, "Roubaix"),
            BranchRecord(3, "Tourcoing"),
        ],
        lines=[
            StockLine(1, "Lille", 10, 5),
            StockLine(2, "Roubaix", 10, 3),
            StockLine(1, "Lille", 20, 2),
            StockLine(2, "Roubaix", 20, 4),
            StockLine(3, "Tourcoing", 30, 1),
            # Zero quantity must never appear as available.
            StockLine(3, "Tourcoing", 10, 0),
        ],
    )


class TestGetProductStock:
    def test_product_available_in_multiple_branches(self) -> None:
        result = get_product_stock(sample_repo(), 10)
        assert result["external_product_id"] == 10
        assert result["total_quantity"] == 8
        assert result["branches"] == [
            {"branch_id": 1, "branch_name": "Lille", "quantity": 5},
            {"branch_id": 2, "branch_name": "Roubaix", "quantity": 3},
        ]

    def test_product_absent_from_all_stocks(self) -> None:
        with pytest.raises(StockNotFoundError):
            get_product_stock(sample_repo(), 999)

    def test_zero_quantity_not_presented_as_available(self) -> None:
        # Product 10 has a zero row in Tourcoing that must be ignored.
        result = get_product_stock(sample_repo(), 10)
        branch_ids = {item["branch_id"] for item in result["branches"]}
        assert 3 not in branch_ids

    @pytest.mark.parametrize("product_id", [None, True, False, 0, -1, 1.5, "1", ""])
    def test_invalid_product_id(self, product_id: object) -> None:
        with pytest.raises(InvalidStockArgumentError):
            get_product_stock(sample_repo(), product_id)


class TestGetBranchStock:
    def test_existing_branch_with_multiple_products(self) -> None:
        result = get_branch_stock(sample_repo(), 1)
        assert result["branch_id"] == 1
        assert result["branch_name"] == "Lille"
        assert result["stocks"] == [
            {"external_product_id": 10, "quantity": 5},
            {"external_product_id": 20, "quantity": 2},
        ]

    def test_branch_by_name_case_insensitive(self) -> None:
        result = get_branch_stock(sample_repo(), "  lille ")
        assert result["branch_id"] == 1
        assert result["branch_name"] == "Lille"

    def test_unknown_branch(self) -> None:
        with pytest.raises(BranchNotFoundError):
            get_branch_stock(sample_repo(), "Unknown")

    def test_unknown_branch_id(self) -> None:
        with pytest.raises(BranchNotFoundError):
            get_branch_stock(sample_repo(), 999)

    def test_branch_with_no_positive_stock(self) -> None:
        repo = FakeStockRepository(
            branches=[BranchRecord(4, "Empty")],
            lines=[StockLine(4, "Empty", 10, 0)],
        )
        result = get_branch_stock(repo, 4)
        assert result["stocks"] == []

    def test_empty_branch_name(self) -> None:
        with pytest.raises(InvalidStockArgumentError):
            get_branch_stock(sample_repo(), "   ")

    def test_no_descriptive_product_fields(self) -> None:
        result = get_branch_stock(sample_repo(), "Roubaix")
        for stock in result["stocks"]:
            assert set(stock.keys()) == {"external_product_id", "quantity"}


class TestCheckShoppingList:
    def test_single_branch_can_fulfill(self) -> None:
        result = check_shopping_list(
            sample_repo(),
            [{"product_id": 10, "quantity": 4}, {"product_id": 20, "quantity": 2}],
        )
        assert result["fulfillable"] is True
        assert result["single_branch_possible"] is True
        assert result["multi_branch_possible"] is False
        assert result["single_branch_candidates"] == [
            {"branch_id": 1, "branch_name": "Lille"},
        ]
        assert result["missing_items"] == []

    def test_multiple_single_branch_candidates(self) -> None:
        repo = FakeStockRepository(
            branches=[
                BranchRecord(1, "Lille"),
                BranchRecord(2, "Roubaix"),
            ],
            lines=[
                StockLine(1, "Lille", 10, 5),
                StockLine(1, "Lille", 20, 5),
                StockLine(2, "Roubaix", 10, 5),
                StockLine(2, "Roubaix", 20, 5),
            ],
        )
        result = check_shopping_list(
            repo,
            [{"product_id": 10, "quantity": 1}, {"product_id": 20, "quantity": 1}],
        )
        assert result["single_branch_possible"] is True
        assert result["single_branch_candidates"] == [
            {"branch_id": 1, "branch_name": "Lille"},
            {"branch_id": 2, "branch_name": "Roubaix"},
        ]

    def test_requires_multiple_branches(self) -> None:
        result = check_shopping_list(
            sample_repo(),
            [{"product_id": 10, "quantity": 7}, {"product_id": 20, "quantity": 5}],
        )
        assert result["single_branch_possible"] is False
        assert result["multi_branch_possible"] is True
        assert result["fulfillable"] is True
        assert result["fulfillment_plan"]
        # Deterministic greedy allocation:
        # product 10: Lille(5) then Roubaix(2); product 20: Roubaix(4) then Lille(1).
        by_branch = {
            entry["branch_id"]: entry for entry in result["fulfillment_plan"]
        }
        assert by_branch[1]["items"] == [
            {"product_id": 10, "quantity": 5},
            {"product_id": 20, "quantity": 1},
        ]
        assert by_branch[2]["items"] == [
            {"product_id": 10, "quantity": 2},
            {"product_id": 20, "quantity": 4},
        ]

    def test_insufficient_cumulative_stock(self) -> None:
        result = check_shopping_list(
            sample_repo(),
            [{"product_id": 10, "quantity": 100}],
        )
        assert result["fulfillable"] is False
        assert result["multi_branch_possible"] is False
        assert result["missing_items"] == [
            {
                "product_id": 10,
                "requested_quantity": 100,
                "available_quantity": 8,
                "missing_quantity": 92,
            }
        ]
        assert result["fulfillment_plan"] == [
            {
                "branch_id": 1,
                "branch_name": "Lille",
                "items": [{"product_id": 10, "quantity": 5}],
            },
            {
                "branch_id": 2,
                "branch_name": "Roubaix",
                "items": [{"product_id": 10, "quantity": 3}],
            },
        ]

    def test_partially_missing_quantity(self) -> None:
        result = check_shopping_list(
            sample_repo(),
            [
                {"product_id": 10, "quantity": 1},
                {"product_id": 30, "quantity": 5},
            ],
        )
        assert result["fulfillable"] is False
        assert result["missing_items"] == [
            {
                "product_id": 30,
                "requested_quantity": 5,
                "available_quantity": 1,
                "missing_quantity": 4,
            }
        ]

    def test_duplicate_products_are_summed(self) -> None:
        merged = normalize_shopping_items(
            [
                {"product_id": 10, "quantity": 2},
                {"product_id": 10, "quantity": 3},
            ]
        )
        assert merged == [{"product_id": 10, "quantity": 5}]
        result = check_shopping_list(
            sample_repo(),
            [
                {"product_id": 10, "quantity": 2},
                {"product_id": 10, "quantity": 3},
            ],
        )
        assert result["requested_items"] == [{"product_id": 10, "quantity": 5}]
        assert result["fulfillable"] is True
        assert result["single_branch_possible"] is True

    def test_empty_list_rejected(self) -> None:
        with pytest.raises(InvalidStockArgumentError):
            check_shopping_list(sample_repo(), [])

    def test_external_product_id_alias_is_rejected(self) -> None:
        with pytest.raises(InvalidStockArgumentError):
            check_shopping_list(
                sample_repo(),
                [{"external_product_id": 10, "quantity": 1}],
            )

    @pytest.mark.parametrize(
        "items",
        [
            None,
            "not-a-list",
            [{"product_id": 1}],
            [{"quantity": 1}],
            [{"product_id": 0, "quantity": 1}],
            [{"product_id": 1, "quantity": 0}],
            [{"product_id": True, "quantity": 1}],
            [{"product_id": 1, "quantity": True}],
            [{"product_id": 1, "quantity": 1.5}],
            [None],
        ],
    )
    def test_invalid_items(self, items: object) -> None:
        with pytest.raises(InvalidStockArgumentError):
            check_shopping_list(sample_repo(), items)

    def test_multi_branch_order_is_stable(self) -> None:
        repo = FakeStockRepository(
            branches=[
                BranchRecord(1, "A"),
                BranchRecord(2, "B"),
                BranchRecord(3, "C"),
            ],
            lines=[
                StockLine(1, "A", 10, 2),
                StockLine(2, "B", 10, 2),
                StockLine(3, "C", 10, 2),
            ],
        )
        first = check_shopping_list(repo, [{"product_id": 10, "quantity": 5}])
        second = check_shopping_list(repo, [{"product_id": 10, "quantity": 5}])
        assert first == second
        # Equal quantities: stable ascending branch_id order after quantity sort.
        assert [entry["branch_id"] for entry in first["fulfillment_plan"]] == [1, 2, 3]


class TestHandlers:
    def test_database_unavailable_is_structured(self) -> None:
        repo = FakeStockRepository(fail_with=DatabaseUnavailableError())
        result = get_product_stock_handler(repo, product_id=1)
        assert result["status"] == "error"
        assert result["error"]["code"] == "DATABASE_UNAVAILABLE"
        assert "traceback" not in str(result).lower()
        assert "password" not in str(result).lower()
        assert "sql" not in str(result).lower()

    def test_sensitive_exception_not_leaked(self) -> None:
        class Boom(Exception):
            pass

        repo = FakeStockRepository(
            fail_with=Boom("postgresql://user:super-secret@db/hbntory password_hash=x")
        )
        result = get_branch_stock_handler(repo, branch=1)
        assert result["status"] == "error"
        assert result["error"]["code"] == "INTERNAL_ERROR"
        serialized = str(result)
        assert "super-secret" not in serialized
        assert "password_hash" not in serialized
        assert "postgresql://" not in serialized

    def test_handler_success_shapes(self) -> None:
        repo = sample_repo()
        product = get_product_stock_handler(repo, product_id=10)
        assert product["status"] == "success"
        branch = get_branch_stock_handler(repo, branch="Roubaix")
        assert branch["status"] == "success"
        shopping = check_shopping_list_handler(
            repo,
            items=[{"product_id": 10, "quantity": 1}],
        )
        assert shopping["status"] == "success"

    def test_malformed_repository_response_is_structured(self) -> None:
        class MalformedRepository(FakeStockRepository):
            def list_product_stock(self, external_product_id: int) -> list[StockLine]:
                del external_product_id
                return [StockLine(1, "Lille", 999, 2)]

        with pytest.raises(InvalidStockResponseError):
            get_product_stock(MalformedRepository(), 10)

        result = get_product_stock_handler(MalformedRepository(), product_id=10)
        assert result["status"] == "error"
        assert result["error"]["code"] == "INVALID_STOCK_RESPONSE"
