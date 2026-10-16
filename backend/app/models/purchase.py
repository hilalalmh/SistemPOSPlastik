import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.dbtypes import UTCDateTime
from app.models.base import UUIDMixin


class Purchase(UUIDMixin, Base):
    __tablename__ = "purchases"

    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    ordered_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    received_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    subtotal: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    discount_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    header_discount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    additional_cost: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    invoice_no: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    received_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )

    items: Mapped[list["PurchaseItem"]] = relationship(
        back_populates="purchase", cascade="all, delete-orphan"
    )


class PurchaseItem(UUIDMixin, Base):
    __tablename__ = "purchase_items"

    purchase_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    conversion_factor: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    received_quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    base_quantity: Mapped[float | None] = mapped_column(Numeric(18, 4))
    unit_cost: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    line_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)

    purchase: Mapped[Purchase] = relationship(back_populates="items")


class PurchaseReceipt(UUIDMixin, Base):
    __tablename__ = "purchase_receipts"

    purchase_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(100), nullable=False)
    received_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    notes: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["PurchaseReceiptItem"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class PurchaseReceiptItem(UUIDMixin, Base):
    __tablename__ = "purchase_receipt_items"

    receipt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_receipts.id", ondelete="CASCADE"), nullable=False
    )
    purchase_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("purchase_items.id"), nullable=False
    )
    base_quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)

    receipt: Mapped[PurchaseReceipt] = relationship(back_populates="items")
