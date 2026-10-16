from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import StockBalance
from app.services import inventory


def _balance(variant_id):
    db = SessionLocal()
    try:
        return db.execute(
            select(StockBalance).where(StockBalance.variant_id == UUID(str(variant_id)))
        ).scalar_one()
    finally:
        db.close()


def test_moving_average_cost(db, make_variant):
    setup = make_variant(stock=0)
    variant_id = UUID(setup["variant_id"])
    location_id = UUID(setup["location_id"])

    inventory.apply_movement(
        db,
        variant_id=variant_id,
        location_id=location_id,
        movement_type="opening",
        quantity_delta=Decimal(100),
        unit_cost=Decimal(10),
    )
    db.commit()
    balance = _balance(variant_id)
    assert balance.quantity == Decimal("100.0000")
    assert balance.avg_cost == Decimal("10.0000")

    inventory.apply_movement(
        db,
        variant_id=variant_id,
        location_id=location_id,
        movement_type="purchase",
        quantity_delta=Decimal(100),
        unit_cost=Decimal(20),
    )
    db.commit()
    balance = _balance(variant_id)
    assert balance.quantity == Decimal("200.0000")
    assert balance.avg_cost == Decimal("15.0000")

    inventory.apply_movement(
        db,
        variant_id=variant_id,
        location_id=location_id,
        movement_type="sale",
        quantity_delta=Decimal(-50),
    )
    db.commit()
    balance = _balance(variant_id)
    assert balance.quantity == Decimal("150.0000")
    assert balance.avg_cost == Decimal("15.0000")


def test_insufficient_stock_blocked(db, make_variant):
    setup = make_variant(stock=Decimal(5))
    variant_id = UUID(setup["variant_id"])
    location_id = UUID(setup["location_id"])

    try:
        inventory.apply_movement(
            db,
            variant_id=variant_id,
            location_id=location_id,
            movement_type="sale",
            quantity_delta=Decimal(-10),
        )
        raise AssertionError("expected insufficient stock error")
    except Exception as exc:  # noqa: BLE001
        assert getattr(exc, "code", None) == "INSUFFICIENT_STOCK"
