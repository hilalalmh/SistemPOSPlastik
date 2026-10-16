from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.inventory import StockBalance
from app.models.product import Product, ProductPrice, ProductUnitConversion, ProductVariant, Unit
from app.models.user import User
from app.permissions import SALE_CREATE
from app.schemas.sale import CatalogItemOut
from app.services.sales import get_default_location_id

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _attributes(variant: ProductVariant) -> dict:
    attrs = {
        "size": variant.attribute_size,
        "color": variant.attribute_color,
        "thickness": variant.attribute_thickness,
        "type": variant.attribute_type,
        "packaging": variant.attribute_packaging,
    }
    return {key: value for key, value in attrs.items() if value}


def build_catalog_item(db: Session, variant: ProductVariant, location_id) -> dict:
    base_unit = db.get(Unit, variant.base_unit_id)
    balance = db.execute(
        select(StockBalance).where(
            StockBalance.variant_id == variant.id,
            StockBalance.location_id == location_id,
        )
    ).scalar_one_or_none()
    stock_base = Decimal(balance.quantity) if balance else Decimal(0)

    conversions = list(
        db.execute(
            select(ProductUnitConversion).where(
                ProductUnitConversion.variant_id == variant.id,
                ProductUnitConversion.is_active.is_(True),
            )
        ).scalars()
    )
    conv_by_unit = {c.unit_id: c for c in conversions}

    prices = list(
        db.execute(
            select(ProductPrice).where(
                ProductPrice.variant_id == variant.id,
                ProductPrice.is_active.is_(True),
            )
        ).scalars()
    )
    price_by_unit: dict = {}
    for price in prices:
        current = price_by_unit.get(price.unit_id)
        if current is None or price.min_qty < current.min_qty:
            price_by_unit[price.unit_id] = price

    unit_ids = [variant.base_unit_id]
    unit_ids += [c.unit_id for c in conversions if c.unit_id != variant.base_unit_id]

    units_payload = []
    for unit_id in unit_ids:
        unit = db.get(Unit, unit_id)
        if unit is None:
            continue
        if unit_id == variant.base_unit_id:
            factor = Decimal(1)
        else:
            conversion = conv_by_unit.get(unit_id)
            if conversion is None:
                continue
            factor = Decimal(conversion.base_units_per_unit)
        price = price_by_unit.get(unit_id)
        units_payload.append(
            {
                "unit_id": str(unit_id),
                "unit_name": unit.name,
                "symbol": unit.symbol,
                "conversion_factor": f"{factor:f}",
                "unit_price": str(price.unit_price) if price else None,
                "min_qty": str(price.min_qty) if price else None,
            }
        )

    price_from = min((Decimal(p.unit_price) for p in prices), default=None)

    return CatalogItemOut(
        variant_id=variant.id,
        product_name=variant.product.name,
        sku=variant.sku,
        barcode=variant.barcode,
        attributes=_attributes(variant),
        base_unit_id=variant.base_unit_id,
        base_unit_name=base_unit.name if base_unit else "",
        stock_base=stock_base,
        price_from=price_from,
        units=units_payload,
    ).model_dump()


@router.get("/search")
def search_catalog(
    q: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=50),
    location_id: UUID | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(SALE_CREATE)),
):
    loc = location_id or get_default_location_id(db)
    stmt = (
        select(ProductVariant)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(ProductVariant.is_active.is_(True), Product.is_active.is_(True))
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            Product.name.ilike(like)
            | ProductVariant.sku.ilike(like)
            | ProductVariant.barcode.ilike(like)
        )
    variants = db.execute(stmt.order_by(Product.name).limit(limit)).scalars().all()
    return {"data": [build_catalog_item(db, v, loc) for v in variants]}


@router.get("/barcode/{barcode}")
def lookup_barcode(
    barcode: str,
    location_id: UUID | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(SALE_CREATE)),
):
    variant = db.execute(
        select(ProductVariant).where(ProductVariant.barcode == barcode)
    ).scalar_one_or_none()
    if variant is None:
        raise NotFoundError("Barcode tidak terdaftar.")
    loc = location_id or get_default_location_id(db)
    return build_catalog_item(db, variant, loc)


@router.get("/variants/{variant_id}/available-units")
def available_units(
    variant_id: UUID,
    location_id: UUID | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(SALE_CREATE)),
):
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("Varian tidak ditemukan.")
    loc = location_id or get_default_location_id(db)
    return build_catalog_item(db, variant, loc)
