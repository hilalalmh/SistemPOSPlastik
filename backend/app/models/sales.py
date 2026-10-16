import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class CashSession(UUIDMixin, Base):
    __tablename__ = "cash_sessions"

    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    cashier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opening_cash: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    expected_cash: Mapped[float | None] = mapped_column(Numeric(18, 2))
    counted_cash: Mapped[float | None] = mapped_column(Numeric(18, 2))
    difference: Mapped[float | None] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    notes: Mapped[str | None] = mapped_column(Text)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class CashMovement(UUIDMixin, Base):
    __tablename__ = "cash_movements"

    cash_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cash_sessions.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    reference_type: Mapped[str | None] = mapped_column(String(30))
    reference_id: Mapped[uuid.UUID | None] = mapped_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class Sale(UUIDMixin, Base):
    __tablename__ = "sales"

    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    cashier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    cash_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cash_sessions.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    subtotal: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    discount_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    tax_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    paid_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    change_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    cost_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    void_reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(150), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan"
    )
    cashier: Mapped["User"] = relationship(foreign_keys=[cashier_id], viewonly=True)


class SaleItem(UUIDMixin, Base):
    __tablename__ = "sale_items"

    sale_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    sku_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    unit_name_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    conversion_factor: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    base_quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    line_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    cost_unit: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    cost_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    sale: Mapped[Sale] = relationship(back_populates="items")


class Payment(UUIDMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_amount"),)

    sale_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales.id", ondelete="CASCADE"), nullable=False
    )
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")
    reference_no: Mapped[str | None] = mapped_column(String(100))
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    sale: Mapped[Sale] = relationship(back_populates="payments")
