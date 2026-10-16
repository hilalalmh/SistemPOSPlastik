from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.common import Page
from app.schemas.purchase import (
    PurchaseCreate,
    PurchaseOut,
    PurchaseUpdate,
    ReceiveRequest,
)
from app.services import audit, purchases
from app.services.sales import get_default_location_id

router = APIRouter(prefix="/purchases", tags=["purchases"])


def _get(db: Session, purchase_id: UUID) -> Purchase:
    purchase = db.execute(
        select(Purchase).options(selectinload(Purchase.items)).where(Purchase.id == purchase_id)
    ).scalar_one_or_none()
    if purchase is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Pembelian tidak ditemukan.", code="PURCHASE_NOT_FOUND")
    return purchase


@router.get("", response_model=Page[PurchaseOut])
def list_purchases(
    status: str | None = None,
    supplier_id: UUID | None = None,
    q: str | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("purchase.read")),
):
    stmt = purchases.purchase_query()
    count_stmt = select(func.count()).select_from(Purchase)

    if status:
        stmt = stmt.where(Purchase.status == status)
        count_stmt = count_stmt.where(Purchase.status == status)
    if supplier_id:
        purchase_filter = Purchase.supplier_id == supplier_id
        stmt = stmt.where(purchase_filter)
        count_stmt = count_stmt.where(purchase_filter)
    if q:
        pattern = f"%{q.strip()}%"
        condition = or_(Purchase.number.ilike(pattern), Purchase.invoice_no.ilike(pattern))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(Purchase.created_at.desc())
            .offset(page.offset)
            .limit(page.page_size)
        )
        .scalars()
        .all()
    )
    return {
        "data": [purchases.serialize_purchase(db, row) for row in rows],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


@router.post("", response_model=PurchaseOut, status_code=201)
def create_purchase(
    payload: PurchaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase.update")),
):
    location_id = payload.location_id or get_default_location_id(db)
    purchase = purchases.create_purchase(
        db, payload, location_id=location_id, created_by=user.id
    )
    audit.log_action(
        db,
        action="purchase.create",
        entity_type="purchase",
        actor_id=user.id,
        entity_id=purchase.id,
        meta={"number": purchase.number, "total": str(purchase.total)},
    )
    db.commit()
    db.refresh(purchase)
    return purchases.serialize_purchase(db, purchase)


@router.get("/{purchase_id}", response_model=PurchaseOut)
def get_purchase(
    purchase_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("purchase.read")),
):
    return purchases.serialize_purchase(db, _get(db, purchase_id))


@router.patch("/{purchase_id}", response_model=PurchaseOut)
def update_purchase(
    purchase_id: UUID,
    payload: PurchaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase.update")),
):
    purchase = purchases.update_purchase(db, _get(db, purchase_id), payload)
    audit.log_action(
        db,
        action="purchase.update",
        entity_type="purchase",
        actor_id=user.id,
        entity_id=purchase.id,
        meta={"number": purchase.number, "total": str(purchase.total)},
    )
    db.commit()
    db.refresh(purchase)
    return purchases.serialize_purchase(db, purchase)


@router.post("/{purchase_id}/order", response_model=PurchaseOut)
def order_purchase(
    purchase_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase.update")),
):
    purchase = purchases.order_purchase(db, _get(db, purchase_id))
    audit.log_action(
        db,
        action="purchase.order",
        entity_type="purchase",
        actor_id=user.id,
        entity_id=purchase.id,
        meta={"number": purchase.number},
    )
    db.commit()
    db.refresh(purchase)
    return purchases.serialize_purchase(db, purchase)


@router.post("/{purchase_id}/receive", response_model=PurchaseOut)
def receive_purchase(
    purchase_id: UUID,
    payload: ReceiveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase.receive")),
):
    purchase = _get(db, purchase_id)
    receipt = purchases.receive_purchase(
        db,
        purchase,
        lines=payload.items,
        received_by=user.id,
        notes=payload.notes,
    )
    audit.log_action(
        db,
        action="purchase.receive",
        entity_type="purchase",
        actor_id=user.id,
        entity_id=purchase.id,
        meta={"number": purchase.number, "receipt": receipt.number},
    )
    db.commit()
    db.refresh(purchase)
    return purchases.serialize_purchase(db, purchase)


@router.post("/{purchase_id}/cancel", response_model=PurchaseOut)
def cancel_purchase(
    purchase_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase.update")),
):
    purchase = purchases.cancel_purchase(db, _get(db, purchase_id))
    audit.log_action(
        db,
        action="purchase.cancel",
        entity_type="purchase",
        actor_id=user.id,
        entity_id=purchase.id,
        meta={"number": purchase.number},
    )
    db.commit()
    db.refresh(purchase)
    return purchases.serialize_purchase(db, purchase)
