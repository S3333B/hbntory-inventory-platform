"""Local stock quantity model."""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backoffice.app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backoffice.app.models.branch import Branch


class Stock(TimestampMixin, Base):
    """A quantity for one external product in one local branch."""

    __tablename__ = "stocks"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_stocks_quantity_non_negative"),
        CheckConstraint(
            "external_product_id > 0",
            name="ck_stocks_external_product_id_positive",
        ),
        UniqueConstraint(
            "branch_id",
            "external_product_id",
            name="uq_stocks_branch_external_product",
        ),
        Index("ix_stocks_external_product_id", "external_product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_product_id: Mapped[int] = mapped_column(nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=0)

    branch: Mapped["Branch"] = relationship(back_populates="stocks")
