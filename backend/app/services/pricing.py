from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.models.product import ProductPrice, ProductUnitConversion, ProductVariant


@dataclass
class ResolvedPrice:
    unit_id: UUID
    unit_price: Decimal
    min_qty: Decimal
    max_qty: Decimal | None


def resolve_conversion_factor(db: Session, variant: ProductVariant, unit_id: UUID) -> Decimal:
    """Return base units per chosen unit. Base unit resolves to 1."""
    if variant.base_unit_id == unit_id:
        return Decimal(1)

    conversion = db.execute(
        select(ProductUnitConversion).where(
            ProductUnitConversion.variant_id == variant.id,
            ProductUnitConversion.unit_id == unit_id,
            ProductUnitConversion.is_active.is_(True),
        )
    ).scalar_one_or_none()

    if conversion is None:
        raise BusinessRuleError(
            "Satuan tidak memiliki konversi yang terdefinisi untuk varian ini.",
            code="CONVERSION_NOT_DEFINED",
        )
    factor = Decimal(conversion.base_units_per_unit)
    if factor <= 0:
        raise BusinessRuleError("Faktor konversi harus positif.", code="INVALID_CONVERSION")
    return factor


def resolve_price(
    db: Session,
    variant_id: UUID,
    unit_id: UUID,
    quantity: Decimal,
    moment: datetime | None = None,
) -> ResolvedPrice:
    """Resolve the applicable tiered price for a quantity (server-side only)."""
    when = moment or datetime.now(UTC)
    qty = Decimal(quantity)
    if qty <= 0:
        raise BusinessRuleError("Kuantitas harus lebih dari nol.", code="INVALID_QUANTITY")

    stmt = (
        select(ProductPrice)
        .where(
            ProductPrice.variant_id == variant_id,
            ProductPrice.unit_id == unit_id,
            ProductPrice.is_active.is_(True),
            ProductPrice.min_qty <= qty,
            or_(ProductPrice.max_qty.is_(None), ProductPrice.max_qty >= qty),
            or_(ProductPrice.valid_from.is_(None), ProductPrice.valid_from <= when),
            or_(ProductPrice.valid_to.is_(None), ProductPrice.valid_to > when),
        )
        .order_by(ProductPrice.min_qty.desc())
    )
    price = db.execute(stmt).scalars().first()

    if price is None:
        raise BusinessRuleError(
            "Harga untuk kombinasi varian, satuan, dan kuantitas ini tidak ditemukan.",
            code="PRICE_NOT_FOUND",
        )

    unit_price = Decimal(price.unit_price)
    if unit_price < 0:
        raise BusinessRuleError("Harga tidak boleh negatif.", code="INVALID_PRICE")

    return ResolvedPrice(
        unit_id=unit_id,
        unit_price=unit_price,
        min_qty=Decimal(price.min_qty),
        max_qty=Decimal(price.max_qty) if price.max_qty is not None else None,
    )
