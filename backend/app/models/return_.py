import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDMixin


class Return(UUIDMixin, Base):
    __tablename__ = "returns"

    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    sale_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sales.id"))
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("purchases.id"))
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    refund_method: Mapped[str | None] = mapped_column(String(30))
    refund_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    items: Mapped[list["ReturnItem"]] = relationship(
        back_populates="return_", cascade="all, delete-orphan"
    )


class ReturnItem(UUIDMixin, Base):
    __tablename__ = "return_items"

    return_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("returns.id", ondelete="CASCADE"), nullable=False
    )
    sale_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sale_items.id"))
    purchase_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("purchase_items.id"))
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    conversion_factor: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    base_quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    condition: Mapped[str] = mapped_column(String(20), nullable=False)
    refund_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)

    return_: Mapped[Return] = relationship(back_populates="items")
