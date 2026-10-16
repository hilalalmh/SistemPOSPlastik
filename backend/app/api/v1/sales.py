from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_user_permissions, require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.timeutil import day_bounds
from app.models.sales import CashMovement, CashSession, Sale
from app.models.store import StoreSetting
from app.models.user import User
from app.permissions import RETURN_READ, SALE_CREATE, SALE_READ, SALE_VOID, SESSION_READ
from app.schemas.return_ import ReturnableSaleOut
from app.schemas.sale import (
    CashMovementCreate,
    CashSessionClose,
    CashSessionOpen,
    CashSessionOut,
    CheckoutRequest,
    QuoteRequest,
    SaleOut,
    VoidRequest,
)
from app.services import audit, idempotency
from app.services import sales as sales_service
from app.services.sales import CartItemInput

router = APIRouter(tags=["sales"])


# --------------------------------------------------------------- cash sessions
@router.post("/cash-sessions/open", response_model=CashSessionOut, status_code=201)
def open_session(
    payload: CashSessionOpen,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("session.open")),
):
    location_id = payload.location_id or sales_service.get_default_location_id(db)
    session = sales_service.open_cash_session(
        db,
        cashier_id=user.id,
        location_id=location_id,
        opening_cash=payload.opening_cash,
        user_id=user.id,
    )
    audit.log_action(
        db,
        action="session.open",
        entity_type="cash_session",
        entity_id=session.id,
        actor_id=user.id,
    )
    db.commit()
    db.refresh(session)
    return session


@router.get("/cash-sessions/current")
def current_session(
    location_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(SESSION_READ)),
):
    loc = location_id or sales_service.get_default_location_id(db)
    session = sales_service.get_open_session(db, user.id, loc)
    return {"data": _session_summary(db, session) if session else None}


@router.get("/cash-sessions")
def list_sessions(
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(SESSION_READ)),
):
    stmt = select(CashSession).order_by(CashSession.opened_at.desc())
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.offset(page.offset).limit(page.page_size)).scalars().all()
    return {
        "data": [CashSessionOut.model_validate(s).model_dump() for s in rows],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


@router.get("/cash-sessions/{session_id}")
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(SESSION_READ)),
):
    session = db.get(CashSession, session_id)
    if session is None:
        raise NotFoundError("Shift tidak ditemukan.")
    data = _session_summary(db, session)
    movements = (
        db.execute(
            select(CashMovement)
            .where(CashMovement.cash_session_id == session.id)
            .order_by(CashMovement.created_at)
        )
        .scalars()
        .all()
    )
    data["movements"] = [
        {
            "id": str(m.id),
            "type": m.type,
            "amount": str(m.amount),
            "reason": m.reason,
            "created_at": m.created_at,
        }
        for m in movements
    ]
    return data


@router.post("/cash-sessions/{session_id}/close", response_model=CashSessionOut)
def close_session(
    session_id: UUID,
    payload: CashSessionClose,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("session.close")),
):
    session = db.get(CashSession, session_id)
    if session is None:
        raise NotFoundError("Shift tidak ditemukan.")
    if session.cashier_id != user.id:
        raise BusinessRuleError(
            "Hanya kasir pemilik shift yang dapat menutup.", code="NOT_SESSION_OWNER"
        )
    sales_service.close_cash_session(
        db,
        session,
        counted_cash=payload.counted_cash,
        closed_by=user.id,
        notes=payload.notes,
    )
    audit.log_action(
        db,
        action="session.close",
        entity_type="cash_session",
        entity_id=session.id,
        actor_id=user.id,
    )
    db.commit()
    db.refresh(session)
    return session


@router.post("/cash-sessions/{session_id}/movements", status_code=201)
def add_cash_movement(
    session_id: UUID,
    payload: CashMovementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("session.cashmove")),
):
    session = db.get(CashSession, session_id)
    if session is None:
        raise NotFoundError("Shift tidak ditemukan.")
    movement = sales_service.add_cash_movement(
        db,
        session,
        movement_type=payload.type,
        amount=payload.amount,
        reason=payload.reason,
        user_id=user.id,
    )
    audit.log_action(
        db,
        action="session.cash_movement",
        entity_type="cash_session",
        entity_id=session.id,
        actor_id=user.id,
        meta={"type": payload.type, "amount": str(payload.amount)},
    )
    db.commit()
    return {"id": str(movement.id), "amount": str(movement.amount)}


def _session_summary(db: Session, session: CashSession) -> dict:
    data = CashSessionOut.model_validate(session).model_dump()
    stats = db.execute(
        select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0)).where(
            Sale.cash_session_id == session.id, Sale.status == "completed"
        )
    ).one()
    data["sales_count"] = stats[0]
    data["sales_total"] = str(stats[1])
    return data


# --------------------------------------------------------------------- quotes
def _cart_inputs(items) -> list[CartItemInput]:
    return [
        CartItemInput(
            variant_id=i.variant_id,
            unit_id=i.unit_id,
            quantity=i.quantity,
            discount_amount=i.discount_amount,
            unit_price_override=i.unit_price_override,
        )
        for i in items
    ]


def _quote_line(line) -> dict:
    return {
        "variant_id": str(line.variant.id),
        "name": line.variant.product.name,
        "sku": line.variant.sku,
        "unit_id": str(line.unit.id),
        "unit_name": line.unit.name,
        "conversion_factor": str(line.conversion_factor),
        "quantity": str(line.quantity),
        "base_quantity": str(line.base_quantity),
        "unit_price": str(line.unit_price),
        "min_qty": str(line.min_qty),
        "max_qty": str(line.max_qty) if line.max_qty is not None else None,
        "discount_amount": str(line.discount_amount),
        "line_total": str(line.line_total),
        "stock_base": str(line.stock_base),
        "stock_sufficient": line.stock_sufficient,
        "price_overridden": line.price_overridden,
    }


@router.post("/sales/quotes")
def create_quote(
    payload: QuoteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(SALE_CREATE)),
):
    location_id = payload.location_id or sales_service.get_default_location_id(db)
    permissions = get_user_permissions(db, user)
    cart = sales_service.compute_cart(
        db,
        _cart_inputs(payload.items),
        location_id,
        allow_price_override="sale.update_price" in permissions,
    )
    return {
        "items": [_quote_line(line) for line in cart.lines],
        "subtotal": str(cart.subtotal),
        "discount_total": str(cart.discount_total),
        "tax_total": str(cart.tax_total),
        "total": str(cart.total),
    }


# ------------------------------------------------------------------- checkout
@router.post("/sales")
def create_sale(
    body: CheckoutRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(SALE_CREATE)),
):
    location_id = body.location_id or sales_service.get_default_location_id(db)
    permissions = get_user_permissions(db, user)

    if idempotency_key:
        replay, stored, status_code = idempotency.check_idempotency(
            db,
            user_id=user.id,
            endpoint="POST /sales",
            key=idempotency_key,
            payload=body.model_dump(mode="json"),
        )
        if replay and stored is not None:
            return JSONResponse(status_code=status_code or 201, content=stored)

    session = sales_service.get_open_session(db, user.id, location_id)
    if session is None:
        raise ConflictError("Kasir harus membuka shift terlebih dahulu.", code="SESSION_REQUIRED")

    try:
        sale = sales_service.checkout(
            db,
            cash_session=session,
            items=_cart_inputs(body.items),
            payments=[p.model_dump() for p in body.payments],
            location_id=location_id,
            cashier_id=user.id,
            customer_id=body.customer_id,
            notes=body.notes,
            allow_price_override="sale.update_price" in permissions,
            discount_override="sale.discount" in permissions,
        )
    except Exception:
        db.rollback()
        raise

    response = SaleOut.model_validate(sale).model_dump(mode="json")
    if idempotency_key:
        idempotency.store_idempotency(
            db,
            user_id=user.id,
            endpoint="POST /sales",
            key=idempotency_key,
            payload=body.model_dump(mode="json"),
            status_code=201,
            response_body=response,
        )
    audit.log_action(
        db,
        action="sale.create",
        entity_type="sale",
        entity_id=sale.id,
        actor_id=user.id,
        meta={"number": sale.number, "total": str(sale.total)},
    )
    db.commit()
    return JSONResponse(status_code=201, content=response)


@router.get("/sales")
def list_sales(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    cashier_id: UUID | None = None,
    status: str | None = None,
    q: str | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(SALE_READ)),
):
    stmt = select(Sale)
    if date_from:
        start, _ = day_bounds(date.fromisoformat(date_from[:10]))
        stmt = stmt.where(Sale.sold_at >= start)
    if date_to:
        _, end = day_bounds(date.fromisoformat(date_to[:10]))
        stmt = stmt.where(Sale.sold_at < end)
    if cashier_id:
        stmt = stmt.where(Sale.cashier_id == cashier_id)
    if status:
        stmt = stmt.where(Sale.status == status)
    if q:
        stmt = stmt.where(Sale.number.ilike(f"%{q.strip()}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(stmt.order_by(Sale.sold_at.desc()).offset(page.offset).limit(page.page_size))
        .scalars()
        .all()
    )
    return {
        "data": [SaleOut.model_validate(s).model_dump() for s in rows],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


@router.get("/sales/{sale_id}", response_model=SaleOut)
def get_sale(
    sale_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(SALE_READ)),
):
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise NotFoundError("Transaksi tidak ditemukan.")
    return sale


@router.get("/sales/{sale_id}/receipt")
def get_receipt(
    sale_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(SALE_READ)),
):
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise NotFoundError("Transaksi tidak ditemukan.")
    settings = db.execute(select(StoreSetting).limit(1)).scalar_one_or_none()
    cashier = db.get(User, sale.cashier_id)
    items = []
    for item in sale.items:
        items.append(
            {
                "name": item.name_snapshot,
                "sku": item.sku_snapshot,
                "quantity": str(item.quantity),
                "unit_name": item.unit_name_snapshot,
                "unit_price": str(item.unit_price),
                "discount_amount": str(item.discount_amount),
                "line_total": str(item.line_total),
            }
        )
    payments = [
        {"method": p.method, "amount": str(p.amount), "status": p.status} for p in sale.payments
    ]
    return {
        "store_name": settings.store_name if settings else "Toko",
        "store_address": settings.address if settings else None,
        "store_phone": settings.phone if settings else None,
        "receipt_header": settings.receipt_header if settings else None,
        "receipt_footer": settings.receipt_footer if settings else None,
        "number": sale.number,
        "sold_at": sale.sold_at,
        "cashier_name": cashier.name if cashier else "",
        "items": items,
        "subtotal": str(sale.subtotal),
        "discount_total": str(sale.discount_total),
        "total": str(sale.total),
        "paid_total": str(sale.paid_total),
        "change_total": str(sale.change_total),
        "payments": payments,
    }


@router.get("/sales/{sale_id}/returnable-items", response_model=ReturnableSaleOut)
def sale_returnable_items(
    sale_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(RETURN_READ)),
):
    from app.services import returns as returns_service

    sale = returns_service.get_sale(db, sale_id)
    return returns_service.serialize_returnable(db, sale)


@router.post("/sales/{sale_id}/void", response_model=SaleOut)
def void_sale(
    sale_id: UUID,
    payload: VoidRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(SALE_VOID)),
):
    from app.services import inventory as inventory_service

    sale = db.get(Sale, sale_id)
    if sale is None:
        raise NotFoundError("Transaksi tidak ditemukan.")
    if sale.status != "completed":
        raise ConflictError("Transaksi tidak dapat dibatalkan.", code="SALE_NOT_COMPLETED")
    if not payload.reason or not payload.reason.strip():
        raise BusinessRuleError("Alasan void wajib diisi.", code="REASON_REQUIRED")

    for item in sale.items:
        inventory_service.apply_movement(
            db,
            variant_id=item.variant_id,
            location_id=sale.location_id,
            movement_type="void",
            quantity_delta=Decimal(item.base_quantity),
            reference_type="sale",
            reference_id=sale.id,
            user_id=user.id,
            reason=f"Void {sale.number}: {payload.reason}",
        )

    cash_paid = sum((Decimal(p.amount) for p in sale.payments if p.method == "cash"), Decimal(0))
    cash_to_drawer = cash_paid - Decimal(sale.change_total)
    if cash_to_drawer > 0:
        db.add(
            CashMovement(
                cash_session_id=sale.cash_session_id,
                type="refund",
                amount=-cash_to_drawer,
                reason=f"Void {sale.number}",
                reference_type="sale",
                reference_id=sale.id,
                user_id=user.id,
            )
        )

    sale.status = "voided"
    sale.voided_at = datetime.now(UTC)
    sale.voided_by = user.id
    sale.void_reason = payload.reason
    audit.log_action(
        db,
        action="sale.void",
        entity_type="sale",
        entity_id=sale.id,
        actor_id=user.id,
        meta={"reason": payload.reason},
    )
    db.commit()
    db.refresh(sale)
    return sale
