"""Read-only SQLAlchemy access to local branch and stock data.

Reuses the Backoffice declarative models without starting Flask and without
exposing any write path. Callers must never pass SQL fragments; all filters are
bound parameters through SQLAlchemy expressions.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Protocol

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backoffice.app.models import Branch, Stock
from product_mcp_server.app.stock_exceptions import (
    DatabaseUnavailableError,
    InvalidStockResponseError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BranchRecord:
    """Minimal branch identity returned to stock tools."""

    branch_id: int
    branch_name: str


@dataclass(frozen=True)
class StockLine:
    """One non-descriptive stock quantity for a branch/product pair."""

    branch_id: int
    branch_name: str
    external_product_id: int
    quantity: int


class SupportsStockRepository(Protocol):
    """Injectable read-only stock repository interface (real or fake)."""

    def get_branch_by_id(self, branch_id: int) -> BranchRecord | None: ...

    def get_branch_by_name(self, name: str) -> BranchRecord | None: ...

    def list_product_stock(self, external_product_id: int) -> list[StockLine]: ...

    def list_branch_stock(self, branch_id: int) -> list[StockLine]: ...

    def list_stock_for_products(
        self,
        external_product_ids: list[int],
    ) -> list[StockLine]: ...


class SqlAlchemyStockRepository:
    """Read-only stock repository backed by SQLAlchemy sessions."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
        except DatabaseUnavailableError:
            raise
        except SQLAlchemyError as exc:
            logger.warning(
                "Database error during stock query (%s)",
                type(exc).__name__,
            )
            raise DatabaseUnavailableError() from exc
        finally:
            session.close()

    def get_branch_by_id(self, branch_id: int) -> BranchRecord | None:
        with self._session() as session:
            branch = session.get(Branch, branch_id)
            if branch is None:
                return None
            return self._to_branch_record(branch)

    def get_branch_by_name(self, name: str) -> BranchRecord | None:
        """Resolve a branch by case-insensitive exact name match."""

        normalized = name.strip()
        with self._session() as session:
            statement: Select[tuple[Branch]] = (
                select(Branch)
                .where(func.lower(Branch.name) == normalized.lower())
                .order_by(Branch.id.asc())
                .limit(1)
            )
            branch = session.scalar(statement)
            if branch is None:
                return None
            return self._to_branch_record(branch)

    def list_product_stock(self, external_product_id: int) -> list[StockLine]:
        """Return positive stock lines for one product across all branches."""

        with self._session() as session:
            statement = (
                select(Stock, Branch)
                .join(Branch, Branch.id == Stock.branch_id)
                .where(
                    Stock.external_product_id == external_product_id,
                    Stock.quantity > 0,
                )
                .order_by(Branch.id.asc())
            )
            rows = session.execute(statement).all()
            return [self._to_stock_line(stock, branch) for stock, branch in rows]

    def list_branch_stock(self, branch_id: int) -> list[StockLine]:
        """Return positive stock lines for one branch."""

        with self._session() as session:
            statement = (
                select(Stock, Branch)
                .join(Branch, Branch.id == Stock.branch_id)
                .where(
                    Stock.branch_id == branch_id,
                    Stock.quantity > 0,
                )
                .order_by(Stock.external_product_id.asc())
            )
            rows = session.execute(statement).all()
            return [self._to_stock_line(stock, branch) for stock, branch in rows]

    def list_stock_for_products(
        self,
        external_product_ids: list[int],
    ) -> list[StockLine]:
        """Return positive stock lines for the given product identifiers."""

        if not external_product_ids:
            return []
        with self._session() as session:
            statement = (
                select(Stock, Branch)
                .join(Branch, Branch.id == Stock.branch_id)
                .where(
                    Stock.external_product_id.in_(external_product_ids),
                    Stock.quantity > 0,
                )
                .order_by(Stock.external_product_id.asc(), Branch.id.asc())
            )
            rows = session.execute(statement).all()
            return [self._to_stock_line(stock, branch) for stock, branch in rows]

    @staticmethod
    def _to_branch_record(branch: Branch) -> BranchRecord:
        branch_id = branch.id
        branch_name = branch.name
        if (
            not isinstance(branch_id, int)
            or isinstance(branch_id, bool)
            or branch_id < 1
            or not isinstance(branch_name, str)
            or not branch_name.strip()
        ):
            raise InvalidStockResponseError()
        return BranchRecord(branch_id=branch_id, branch_name=branch_name)

    @staticmethod
    def _to_stock_line(stock: Stock, branch: Branch) -> StockLine:
        branch_id = branch.id
        branch_name = branch.name
        product_id = stock.external_product_id
        quantity = stock.quantity
        if (
            not isinstance(branch_id, int)
            or isinstance(branch_id, bool)
            or branch_id < 1
            or not isinstance(branch_name, str)
            or not branch_name.strip()
            or not isinstance(product_id, int)
            or isinstance(product_id, bool)
            or product_id < 1
            or not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity < 0
        ):
            raise InvalidStockResponseError()
        return StockLine(
            branch_id=branch_id,
            branch_name=branch_name,
            external_product_id=product_id,
            quantity=quantity,
        )
