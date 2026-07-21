"""Database model and constraint tests."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backoffice.app.models import Branch, Stock, User, UserRole


def make_user(
    username: str,
    role: UserRole,
    *,
    branch_id: int | None = None,
    password: str = "test-only-password",
) -> User:
    user = User(username=username, role=role, branch_id=branch_id)
    user.set_password(password)
    return user


def test_create_branch(session: Session) -> None:
    branch = Branch(name="  Lille  ")
    session.add(branch)
    session.commit()

    assert branch.id is not None
    assert branch.name == "Lille"


def test_branch_names_are_unique_ignoring_case(session: Session) -> None:
    session.add(Branch(name="Lille"))
    session.commit()
    session.add(Branch(name="lille"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_create_common_user_assigned_to_branch(session: Session) -> None:
    branch = Branch(name="Lille")
    session.add(branch)
    session.flush()
    user = make_user("sebastien", UserRole.COMMON, branch_id=branch.id)
    session.add(user)
    session.commit()

    assert user.branch == branch
    assert user in branch.users


def test_create_admin_without_branch(session: Session) -> None:
    admin = make_user("admin", UserRole.ADMIN)
    session.add(admin)
    session.commit()

    assert admin.branch_id is None
    assert admin.role == "admin"


def test_common_user_without_branch_is_rejected(session: Session) -> None:
    session.add(make_user("common-without-branch", UserRole.COMMON))

    with pytest.raises(IntegrityError):
        session.commit()


def test_admin_with_branch_is_rejected(session: Session) -> None:
    branch = Branch(name="Lille")
    session.add(branch)
    session.flush()
    session.add(make_user("admin", UserRole.ADMIN, branch_id=branch.id))

    with pytest.raises(IntegrityError):
        session.commit()


def test_duplicate_username_is_rejected(session: Session) -> None:
    session.add(make_user("same-user", UserRole.ADMIN))
    session.commit()
    branch = Branch(name="Lille")
    session.add(branch)
    session.flush()
    session.add(make_user("same-user", UserRole.COMMON, branch_id=branch.id))

    with pytest.raises(IntegrityError):
        session.commit()


def test_invalid_role_is_rejected_before_persistence() -> None:
    with pytest.raises(ValueError, match="admin.*common"):
        make_user("invalid-role", "manager")  # type: ignore[arg-type]


def test_soft_delete_keeps_user_row(session: Session) -> None:
    admin = make_user("admin", UserRole.ADMIN)
    session.add(admin)
    session.commit()
    admin_id = admin.id

    admin.soft_delete()
    session.commit()

    stored_user = session.get(User, admin_id)
    assert stored_user is not None
    assert stored_user.is_deleted
    assert stored_user.deleted_at is not None


def test_create_valid_stock(session: Session) -> None:
    branch = Branch(name="Lille")
    session.add(branch)
    session.flush()
    stock = Stock(branch_id=branch.id, external_product_id=1, quantity=12)
    session.add(stock)
    session.commit()

    assert stock.branch == branch
    assert stock.quantity == 12


def test_duplicate_branch_product_stock_is_rejected(session: Session) -> None:
    branch = Branch(name="Lille")
    session.add(branch)
    session.flush()
    session.add(Stock(branch_id=branch.id, external_product_id=1, quantity=2))
    session.commit()
    session.add(Stock(branch_id=branch.id, external_product_id=1, quantity=3))

    with pytest.raises(IntegrityError):
        session.commit()


def test_negative_stock_is_rejected_by_database(session: Session) -> None:
    branch = Branch(name="Lille")
    session.add(branch)
    session.flush()
    session.add(Stock(branch_id=branch.id, external_product_id=1, quantity=-1))

    with pytest.raises(IntegrityError):
        session.commit()


def test_missing_branch_is_rejected_by_foreign_key(session: Session) -> None:
    session.add(Stock(branch_id=999, external_product_id=1, quantity=1))

    with pytest.raises(IntegrityError):
        session.commit()


def test_branch_with_users_or_stock_cannot_be_deleted(session: Session) -> None:
    branch = Branch(name="Lille")
    session.add(branch)
    session.flush()
    session.add(make_user("common-user", UserRole.COMMON, branch_id=branch.id))
    session.add(Stock(branch_id=branch.id, external_product_id=1, quantity=1))
    session.commit()

    session.delete(branch)
    with pytest.raises(IntegrityError):
        session.commit()


def test_stock_contains_no_product_metadata_columns() -> None:
    assert set(Stock.__table__.columns.keys()) == {
        "id",
        "branch_id",
        "external_product_id",
        "quantity",
        "created_at",
        "updated_at",
    }
