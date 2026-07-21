"""Internal Backoffice user model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from werkzeug.security import generate_password_hash

from backoffice.app.models.base import Base, TimestampMixin, utc_now

if TYPE_CHECKING:
    from backoffice.app.models.branch import Branch


class UserRole(str, Enum):
    """Supported Backoffice authorization roles."""

    ADMIN = "admin"
    COMMON = "common"


class User(TimestampMixin, Base):
    """An administrator or branch-scoped common user."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        CheckConstraint(
            "role IN ('admin', 'common')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "(role = 'admin' AND branch_id IS NULL) OR "
            "(role = 'common' AND branch_id IS NOT NULL)",
            name="ck_users_role_branch",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    branch: Mapped["Branch | None"] = relationship(back_populates="users")

    @property
    def is_deleted(self) -> bool:
        """Report whether this user was soft-deleted."""

        return self.deleted_at is not None

    @validates("username")
    def validate_username(self, _key: str, value: str) -> str:
        """Store a non-empty normalized username."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("Username must be a non-empty string.")
        return value.strip()

    @validates("role")
    def validate_role(self, _key: str, value: str | UserRole) -> str:
        """Reject unsupported role values before persistence."""

        normalized = value.value if isinstance(value, UserRole) else value
        if normalized not in {UserRole.ADMIN.value, UserRole.COMMON.value}:
            raise ValueError("Role must be 'admin' or 'common'.")
        return normalized

    def set_password(self, password: str) -> None:
        """Hash a non-empty password with PBKDF2 without storing the clear text."""

        if not isinstance(password, str) or not password:
            raise ValueError("Password must be a non-empty string.")
        self.password_hash = generate_password_hash(
            password,
            method="pbkdf2:sha256:600000",
            salt_length=16,
        )

    def soft_delete(self) -> None:
        """Mark the user as deleted without removing its database row."""

        if self.deleted_at is None:
            self.deleted_at = utc_now()
