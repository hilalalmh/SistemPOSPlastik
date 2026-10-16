from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.inventory import (
    StockAdjustment,
    StockBalance,
    StockCount,
    StockCountItem,
    StockMovement,
)
from app.models.product import Product, ProductVariant, Unit
from app.models.store import Location
from app.models.user import User
from app.schemas.inventory import (
    AdjustmentCreate,
    StockMovementOut,
)
from app.services import audit
from app.services.numbering import generate_number

router = APIRouter(tags=["inventory"])


def _balance_out(db: Session, balance: StockBalance) -> dict:
    variant = db.get(ProductVariant, balance.variant_id)
    unit = db.get(Unit, variant.base_unit_id) if variant else None
    data = {
        "variant_id": balance.variant_id,
        "location_id": balance.location_id,
        "quantity": balance.quantity,
        "avg_cost": balance.avg_cost,
        "updated_at": balance.updated_at,
        "sku": variant.sku if variant else None,
        "product_name": variant.product.name if variant else None,
        "unit_name": unit.name if unit else None,
        "min_stock": variant.min_stock if variant else None,
        "low_stock": bool(
            variant
            and variant.min_stock is not None
            and Decimal(balance.quantity) < Decimal(variant.min_stock)
        ),
    }
    return data


@router.get("/inventory/stock")
def list_stock(
    q: str | None = None,
    low_stock: bool | None = None,
    location_id: UUID | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory.read")),
):
    stmt = select(StockBalance).join(ProductVariant, ProductVariant.id == StockBalance.variant_id)
    if location_id:
        stmt = stmt.where(StockBalance.location_id == location_id)
    if q:
        stmt = stmt.where(
            ProductVariant.sku.ilike(f"%{q}%")
            | ProductVariant.product.has(Product.name.ilike(f"%{q}%"))
        )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(stmt.order_by(ProductVariant.sku).offset(page.offset).limit(page.page_size))
        .scalars()
        .all()
    )
    data = [_balance_out(db, row) for row in rows]
    if low_stock:
        data = [row for row in data if row["low_stock"]]
    return {"data": data, "page": page.page, "page_size": page.page_size, "total": total}


@router.get("/inventory/low-stock")
def low_stock(
    db: Session = Depends(get_db), _: User = Depends(require_permission("inventory.read"))
):
    rows = db.execute(select(StockBalance).join(ProductVariant)).scalars().all()
    data = [r for r in (_balance_out(db, row) for row in rows) if r["low_stock"]]
    return {"data": data, "total": len(data)}


@router.get("/inventory/stock/{variant_id}")
def get_stock(
    variant_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory.read")),
):
    balances = (
        db.execute(select(StockBalance).where(StockBalance.variant_id == variant_id))
        .scalars()
        .all()
    )
    return {"data": [_balance_out(db, b) for b in balances]}


@router.get("/inventory/movements")
def list_movements(
    variant_id: UUID | None = None,
    type: str | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory.read")),
):
    stmt = select(StockMovement)
    if variant_id:
        stmt = stmt.where(StockMovement.variant_id == variant_id)
    if type:
        stmt = stmt.where(StockMovement.type == type)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(StockMovement.created_at.desc()).offset(page.offset).limit(page.page_size)
        )
        .scalars()
        .all()
    )
    data = []
    for row in rows:
        payload = StockMovementOut.model_validate(row).model_dump()
        variant = db.get(ProductVariant, row.variant_id)
        payload["product_name"] = variant.product.name if variant else None
        data.append(payload)
    return {"data": data, "page": page.page, "page_size": page.page_size, "total": total}


@router.post("/inventory/adjustments", response_model=dict, status_code=201)
def create_adjustment(
    payload: AdjustmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("inventory.adjust")),
):
    from app.services import inventory as inventory_service

    if not payload.reason or not payload.reason.strip():
        raise BusinessRuleError("Alasan penyesuaian wajib diisi.", code="REASON_REQUIRED")
    if payload.quantity <= 0:
        raise BusinessRuleError("Kuantitas penyesuaian harus positif.", code="INVALID_QUANTITY")
    if payload.adjustment_type not in {"increase", "decrease"}:
        raise BusinessRuleError("Jenis penyesuaian tidak valid.", code="INVALID_ADJUSTMENT_TYPE")

    variant = db.get(ProductVariant, payload.variant_id)
    if variant is None:
        raise NotFoundError("Varian tidak ditemukan.")

    location_id = payload.location_id or _default_location(db)
    delta = payload.quantity if payload.adjustment_type == "increase" else -payload.quantity
    movement_type = "adjustment_in" if delta > 0 else "adjustment_out"

    adjustment = StockAdjustment(
        number=generate_number(db, "ADJ"),
        location_id=location_id,
        variant_id=payload.variant_id,
        adjustment_type=payload.adjustment_type,
        quantity=payload.quantity,
        reason=payload.reason,
        created_by=user.id,
    )
    db.add(adjustment)
    db.flush()

    movement, _balance = inventory_service.apply_movement(
        db,
        variant_id=payload.variant_id,
        location_id=location_id,
        movement_type=movement_type,
        quantity_delta=delta,
        reference_type="adjustment",
        reference_id=adjustment.id,
        user_id=user.id,
        reason=payload.reason,
    )
    audit.log_action(
        db,
        action="inventory.adjustment",
        entity_type="stock_adjustment",
        entity_id=adjustment.id,
        actor_id=user.id,
        meta={"reason": payload.reason, "quantity": str(payload.quantity)},
    )
    db.commit()
    return {
        "id": str(adjustment.id),
        "number": adjustment.number,
        "balance_after": str(movement.balance_after),
    }


def _default_location(db: Session) -> UUID:
    location = db.execute(
        select(Location).where(Location.is_default.is_(True)).limit(1)
    ).scalar_one_or_none()
    if location is None:
        location = db.execute(select(Location).limit(1)).scalar_one_or_none()
    if location is None:
        raise BusinessRuleError("Lokasi toko belum dikonfigurasi.", code="LOCATION_MISSING")
    return location.id


@router.get("/inventory/adjustments")
def list_adjustments(
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("inventory.read")),
):
    stmt = select(StockAdjustment).order_by(StockAdjustment.created_at.desc())
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.offset(page.offset).limit(page.page_size)).scalars().all()
    return {
        "data": [
            {
                "id": str(r.id),
                "number": r.number,
                "variant_id": str(r.variant_id),
                "adjustment_type": r.adjustment_type,
                "quantity": str(r.quantity),
                "reason": r.reason,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


# ------------------------------------------------------------------ stock count
@router.post("/stock-counts", status_code=201)
def create_stock_count(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("stockcount.create")),
):

    location_id = payload.get("location_id") or _default_location(db)
    notes = payload.get("notes")

    count = StockCount(
        number=generate_number(db, "STO"),
        location_id=location_id,
        status="counting",
        created_by=user.id,
        notes=notes,
    )
    db.add(count)
    db.flush()

    balances = (
        db.execute(select(StockBalance).where(StockBalance.location_id == location_id))
        .scalars()
        .all()
    )
    variants = (
        db.execute(select(ProductVariant).where(ProductVariant.is_active.is_(True))).scalars().all()
    )
    balance_by_variant = {b.variant_id: b for b in balances}
    for variant in variants:
        balance = balance_by_variant.get(variant.id)
        db.add(
            StockCountItem(
                stock_count_id=count.id,
                variant_id=variant.id,
                system_quantity=Decimal(balance.quantity) if balance else Decimal(0),
                unit_id=variant.base_unit_id,
            )
        )
    audit.log_action(
        db,
        action="stockcount.create",
        entity_type="stock_count",
        entity_id=count.id,
        actor_id=user.id,
    )
    db.commit()
    return {"id": str(count.id), "number": count.number, "status": count.status}


@router.get("/stock-counts")
def list_stock_counts(
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stockcount.read")),
):
    stmt = select(StockCount).order_by(StockCount.created_at.desc())
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.offset(page.offset).limit(page.page_size)).scalars().all()
    return {
        "data": [
            {
                "id": str(r.id),
                "number": r.number,
                "status": r.status,
                "created_at": r.created_at,
                "confirmed_at": r.confirmed_at,
            }
            for r in rows
        ],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


def _serialize_count(db: Session, count: StockCount) -> dict:
    items = []
    for item in count.items:
        variant = db.get(ProductVariant, item.variant_id)
        unit = db.get(Unit, item.unit_id)
        items.append(
            {
                "id": str(item.id),
                "variant_id": str(item.variant_id),
                "system_quantity": str(item.system_quantity),
                "counted_quantity": str(item.counted_quantity)
                if item.counted_quantity is not None
                else None,
                "difference": str(item.difference) if item.difference is not None else None,
                "unit_id": str(item.unit_id),
                "unit_name": unit.name if unit else None,
                "notes": item.notes,
                "sku": variant.sku if variant else None,
                "product_name": variant.product.name if variant else None,
            }
        )
    return {
        "id": str(count.id),
        "number": count.number,
        "location_id": str(count.location_id),
        "status": count.status,
        "created_by": str(count.created_by),
        "confirmed_by": str(count.confirmed_by) if count.confirmed_by else None,
        "confirmed_at": count.confirmed_at,
        "notes": count.notes,
        "created_at": count.created_at,
        "items": items,
    }


@router.get("/stock-counts/{count_id}")
def get_stock_count(
    count_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stockcount.read")),
):
    count = db.get(StockCount, count_id)
    if count is None:
        raise NotFoundError("Stok opname tidak ditemukan.")
    return _serialize_count(db, count)


@router.patch("/stock-counts/{count_id}/items")
def update_stock_count_items(
    count_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("stockcount.count")),
):
    count = db.get(StockCount, count_id)
    if count is None:
        raise NotFoundError("Stok opname tidak ditemukan.")
    if count.status != "counting":
        raise ConflictError("Stok opname tidak dalam status penghitungan.", code="INVALID_STATUS")

    by_variant = {item.variant_id: item for item in count.items}
    for raw in payload.get("items", []):
        variant_id = UUID(str(raw["variant_id"]))
        item = by_variant.get(variant_id)
        if item is None:
            raise NotFoundError(f"Item varian {variant_id} tidak ada dalam opname.")
        counted = Decimal(str(raw["counted_quantity"]))
        item.counted_quantity = counted
        item.difference = counted - Decimal(item.system_quantity)
        item.notes = raw.get("notes")
    db.commit()
    return _serialize_count(db, db.get(StockCount, count_id))


@router.post("/stock-counts/{count_id}/confirm")
def confirm_stock_count(
    count_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("stockcount.confirm")),
):
    from app.services import inventory as inventory_service

    count = db.get(StockCount, count_id)
    if count is None:
        raise NotFoundError("Stok opname tidak ditemukan.")
    if count.status != "counting":
        raise ConflictError("Stok opname sudah diproses.", code="INVALID_STATUS")

    for item in count.items:
        if item.counted_quantity is None:
            raise BusinessRuleError(
                "Semua item harus dihitung sebelum konfirmasi.", code="COUNT_INCOMPLETE"
            )
        diff = Decimal(item.counted_quantity) - Decimal(item.system_quantity)
        if diff == 0:
            continue
        inventory_service.apply_movement(
            db,
            variant_id=item.variant_id,
            location_id=count.location_id,
            movement_type="adjustment_in" if diff > 0 else "adjustment_out",
            quantity_delta=diff,
            reference_type="stock_count",
            reference_id=count.id,
            user_id=user.id,
            reason=f"Stok opname {count.number}",
        )

    count.status = "confirmed"
    count.confirmed_by = user.id
    count.confirmed_at = datetime.now(UTC)
    audit.log_action(
        db,
        action="stockcount.confirm",
        entity_type="stock_count",
        entity_id=count.id,
        actor_id=user.id,
    )
    db.commit()
    return _serialize_count(db, count)


@router.post("/stock-counts/{count_id}/cancel")
def cancel_stock_count(
    count_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("stockcount.confirm")),
):
    count = db.get(StockCount, count_id)
    if count is None:
        raise NotFoundError("Stok opname tidak ditemukan.")
    if count.status == "confirmed":
        raise ConflictError(
            "Stok opname yang sudah dikonfirmasi tidak dapat dibatalkan.", code="ALREADY_CONFIRMED"
        )
    count.status = "cancelled"
    audit.log_action(
        db,
        action="stockcount.cancel",
        entity_type="stock_count",
        entity_id=count.id,
        actor_id=user.id,
    )
    db.commit()
    return _serialize_count(db, count)
