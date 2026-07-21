"""Branch model."""

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from backoffice.app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backoffice.app.models.stock import Stock
    from backoffice.app.models.user import User


class Branch(TimestampMixin, Base):
    """A physical branch that owns users and stock quantities."""

    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    __table_args__ = (
        Index("uq_branches_name_lower", func.lower(name), unique=True),
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="branch",
        passive_deletes="all",
    )
    stocks: Mapped[list["Stock"]] = relationship(
        back_populates="branch",
        passive_deletes="all",
    )

    @validates("name")
    def validate_name(self, _key: str, value: str) -> str:
        """Store a non-empty normalized branch name."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError("Branch name must be a non-empty string.")
        return value.strip()
