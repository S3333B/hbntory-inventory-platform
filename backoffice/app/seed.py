"""Idempotent initial data creation for the Backoffice database."""

from dataclasses import dataclass

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from backoffice.app.database import create_schema, make_session_factory
from backoffice.app.models import Branch, Stock, User, UserRole
from backoffice.app.services.product_validation import ProductValidator

INITIAL_BRANCHES = ("Lille", "Roubaix")
INITIAL_EXTERNAL_PRODUCT_ID = 1
INITIAL_STOCK_QUANTITIES = {"Lille": 12, "Roubaix": 8}


class InitializationError(RuntimeError):
    """Raised when safe, deterministic initialization is not possible."""


@dataclass(frozen=True)
class InitializationResult:
    """Identifiers returned after successful initialization."""

    admin_id: int
    branch_ids: dict[str, int]
    stock_ids: dict[str, int]


def initialize_data(
    session: Session,
    *,
    admin_password: str,
    product_validator: ProductValidator,
) -> InitializationResult:
    """Create the initial administrator, branches, and stock without duplicates."""

    if not isinstance(admin_password, str) or not admin_password:
        raise InitializationError(
            "INITIAL_ADMIN_PASSWORD is required and must not be empty."
        )
    if not product_validator.exists(INITIAL_EXTERNAL_PRODUCT_ID):
        raise InitializationError(
            "Initial external product 1 is not accepted by the product validator."
        )

    administrators = list(
        session.scalars(select(User).where(User.role == UserRole.ADMIN.value))
    )
    if len(administrators) > 1:
        raise InitializationError("More than one administrator already exists.")

    admin = session.scalar(select(User).where(User.username == "admin"))
    if admin is not None and (
        admin.role != UserRole.ADMIN.value or admin.branch_id is not None
    ):
        raise InitializationError(
            "The existing 'admin' user does not satisfy administrator constraints."
        )
    if administrators and administrators[0].username != "admin":
        raise InitializationError(
            "An administrator exists but does not use the required 'admin' username."
        )
    if admin is None:
        admin = User(username="admin", role=UserRole.ADMIN, branch_id=None)
        admin.set_password(admin_password)
        session.add(admin)

    branches: dict[str, Branch] = {}
    for branch_name in INITIAL_BRANCHES:
        branch = session.scalar(select(Branch).where(Branch.name == branch_name))
        if branch is None:
            branch = Branch(name=branch_name)
            session.add(branch)
        branches[branch_name] = branch

    session.flush()

    stocks: dict[str, Stock] = {}
    for branch_name, quantity in INITIAL_STOCK_QUANTITIES.items():
        branch = branches[branch_name]
        stock = session.scalar(
            select(Stock).where(
                Stock.branch_id == branch.id,
                Stock.external_product_id == INITIAL_EXTERNAL_PRODUCT_ID,
            )
        )
        if stock is None:
            stock = Stock(
                branch_id=branch.id,
                external_product_id=INITIAL_EXTERNAL_PRODUCT_ID,
                quantity=quantity,
            )
            session.add(stock)
        stocks[branch_name] = stock

    session.flush()
    return InitializationResult(
        admin_id=admin.id,
        branch_ids={name: branch.id for name, branch in branches.items()},
        stock_ids={name: stock.id for name, stock in stocks.items()},
    )


def initialize_database(
    engine: Engine,
    *,
    admin_password: str,
    product_validator: ProductValidator,
    session_factory: sessionmaker[Session] | None = None,
) -> InitializationResult:
    """Create the initial schema and commit deterministic seed data."""

    create_schema(engine)
    factory = session_factory or make_session_factory(engine)
    with factory.begin() as session:
        return initialize_data(
            session,
            admin_password=admin_password,
            product_validator=product_validator,
        )
