import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
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
from app.models.base import TimestampMixin, UUIDMixin


class Category(UUIDMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id")


class Unit(UUIDMixin, Base):
    __tablename__ = "units"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    allows_fraction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    brand: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    category: Mapped[Category | None] = relationship()
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("min_stock IS NULL OR min_stock >= 0", name="ck_variant_min_stock"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True)
    attribute_size: Mapped[str | None] = mapped_column(String(100))
    attribute_color: Mapped[str | None] = mapped_column(String(100))
    attribute_thickness: Mapped[str | None] = mapped_column(String(100))
    attribute_type: Mapped[str | None] = mapped_column(String(100))
    attribute_packaging: Mapped[str | None] = mapped_column(String(100))
    base_unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    min_stock: Mapped[float | None] = mapped_column(Numeric(18, 4))
    cost_method: Mapped[str] = mapped_column(String(20), nullable=False, default="moving_average")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product: Mapped[Product] = relationship(back_populates="variants")
    base_unit: Mapped[Unit] = relationship()
    conversions: Mapped[list["ProductUnitConversion"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    prices: Mapped[list["ProductPrice"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )

    @property
    def product_name(self) -> str | None:
        return self.product.name if self.product is not None else None


class ProductUnitConversion(UUIDMixin, Base):
    __tablename__ = "product_unit_conversions"
    __table_args__ = (
        UniqueConstraint("variant_id", "unit_id", name="uq_conversion_variant_unit"),
        CheckConstraint("base_units_per_unit > 0", name="ck_conversion_positive"),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    base_units_per_unit: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    variant: Mapped[ProductVariant] = relationship(back_populates="conversions")
    unit: Mapped[Unit] = relationship()


class ProductPrice(UUIDMixin, Base):
    __tablename__ = "product_prices"
    __table_args__ = (
        CheckConstraint("min_qty >= 0", name="ck_price_min_qty"),
        CheckConstraint("max_qty IS NULL OR max_qty >= min_qty", name="ck_price_range"),
        CheckConstraint("unit_price >= 0", name="ck_price_unit_price"),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    min_qty: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    max_qty: Mapped[float | None] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    variant: Mapped[ProductVariant] = relationship(back_populates="prices")
    unit: Mapped[Unit] = relationship()


class PriceHistory(UUIDMixin, Base):
    __tablename__ = "price_histories"

    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    old_price: Mapped[float | None] = mapped_column(Numeric(18, 2))
    new_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
