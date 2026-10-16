from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.models.inventory import StockBalance, StockMovement
from app.models.store import StoreSetting


def lock_balance(
    db: Session, variant_id: UUID, location_id: UUID, *, create: bool = True
) -> StockBalance:
    """Fetch a stock balance row with a row-level lock.

    Caller must be inside a transaction. Locks prevent concurrent overselling
    (production.md Bagian 5 butir 6).
    """
    balance = db.execute(
        select(StockBalance)
        .where(
            StockBalance.variant_id == variant_id,
            StockBalance.location_id == location_id,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if balance is None and create:
        balance = StockBalance(
            variant_id=variant_id,
            location_id=location_id,
            quantity=Decimal(0),
            avg_cost=Decimal(0),
        )
        db.add(balance)
        db.flush()
        # Re-lock the freshly created row so concurrent inserts serialize on it.
        balance = db.execute(
            select(StockBalance)
            .where(
                StockBalance.variant_id == variant_id,
                StockBalance.location_id == location_id,
            )
            .with_for_update()
        ).scalar_one()
    return balance


def _allow_negative_stock(db: Session) -> bool:
    setting = db.execute(select(StoreSetting).limit(1)).scalar_one_or_none()
    return bool(setting and setting.allow_negative_stock)


def apply_movement(
    db: Session,
    *,
    variant_id: UUID,
    location_id: UUID,
    movement_type: str,
    quantity_delta: Decimal,
    unit_cost: Decimal | None = None,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    user_id: UUID | None = None,
    reason: str | None = None,
) -> tuple[StockMovement, StockBalance]:
    """Apply a signed stock movement and update the running balance atomically.

    - Incoming quantities with a unit_cost update the moving weighted average.
    - Outgoing quantities keep the average and are costed at the current average.
    - Negative balances are rejected unless explicitly allowed by store settings.
    """
    delta = Decimal(quantity_delta)
    if delta == 0:
        raise BusinessRuleError("Jumlah pergerakan stok tidak boleh nol.", code="INVALID_MOVEMENT")

    balance = lock_balance(db, variant_id, location_id)
    old_qty = Decimal(balance.quantity)
    old_avg = Decimal(balance.avg_cost)
    new_qty = old_qty + delta

    if new_qty < 0 and not _allow_negative_stock(db):
        raise BusinessRuleError(
            f"Stok tidak mencukupi. Tersedia {old_qty} satuan dasar.",
            code="INSUFFICIENT_STOCK",
        )

    if delta > 0 and unit_cost is not None:
        cost = Decimal(unit_cost)
        if new_qty > 0:
            new_avg = ((old_qty * old_avg) + (delta * cost)) / new_qty
        else:
            new_avg = cost
        balance.avg_cost = new_avg.quantize(Decimal("0.0001"))
    elif delta > 0 and old_qty <= 0:
        # Incoming stock with no known cost and no prior stock: keep average as is.
        balance.avg_cost = old_avg

    balance.quantity = new_qty.quantize(Decimal("0.0001"))
    balance.updated_at = datetime.now(UTC)

    movement = StockMovement(
        variant_id=variant_id,
        location_id=location_id,
        type=movement_type,
        quantity=delta.quantize(Decimal("0.0001")),
        unit_cost=Decimal(unit_cost).quantize(Decimal("0.0001")) if unit_cost is not None else None,
        balance_after=balance.quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        user_id=user_id,
        reason=reason,
    )
    db.add(movement)
    db.flush()
    return movement, balance
