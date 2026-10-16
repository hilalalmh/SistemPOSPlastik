from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import ProductVariant, StockBalance
from app.services import pricing


def _balance(variant_id):
    db = SessionLocal()
    try:
        return db.execute(
            select(StockBalance).where(StockBalance.variant_id == UUID(variant_id))
        ).scalar_one()
    finally:
        db.close()


def test_resolve_base_unit_price(db, make_variant):
    setup = make_variant(stock=0)
    resolved = pricing.resolve_price(
        db, UUID(setup["variant_id"]), UUID(setup["unit_pcs"]), Decimal(5)
    )
    assert resolved.unit_price == Decimal("800.00")


def test_resolve_pak_price(db, make_variant):
    setup = make_variant(stock=0)
    resolved = pricing.resolve_price(
        db, UUID(setup["variant_id"]), UUID(setup["unit_pak"]), Decimal(1)
    )
    assert resolved.unit_price == Decimal("7000.00")


def test_conversion_factor(db, make_variant):
    setup = make_variant(stock=0)
    variant = db.get(ProductVariant, UUID(setup["variant_id"]))
    assert pricing.resolve_conversion_factor(db, variant, UUID(setup["unit_pcs"])) == Decimal(1)
    assert pricing.resolve_conversion_factor(db, variant, UUID(setup["unit_pak"])) == Decimal(10)
