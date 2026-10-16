import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDMixin


class StockBalance(UUIDMixin, Base):
    __tablename__ = "stock_balances"
    __table_args__ = (UniqueConstraint("variant_id", "location_id", name="uq_balance_variant_loc"),)

    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    avg_cost: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class StockMovement(UUIDMixin, Base):
    __tablename__ = "stock_movements"

    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(18, 4))
    balance_after: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(30))
    reference_id: Mapped[uuid.UUID | None] = mapped_column()
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class StockAdjustment(UUIDMixin, Base):
    __tablename__ = "stock_adjustments"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_adjustment_quantity"),)

    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    adjustment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class StockCount(UUIDMixin, Base):
    __tablename__ = "stock_counts"

    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="counting")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    items: Mapped[list["StockCountItem"]] = relationship(
        back_populates="stock_count", cascade="all, delete-orphan"
    )


class StockCountItem(UUIDMixin, Base):
    __tablename__ = "stock_count_items"
    __table_args__ = (
        UniqueConstraint("stock_count_id", "variant_id", name="uq_count_item_variant"),
    )

    stock_count_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stock_counts.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    system_quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    counted_quantity: Mapped[float | None] = mapped_column(Numeric(18, 4))
    difference: Mapped[float | None] = mapped_column(Numeric(18, 4))
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    stock_count: Mapped[StockCount] = relationship(back_populates="items")
