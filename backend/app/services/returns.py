from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.product import ProductVariant
from app.models.return_ import Return, ReturnItem
from app.models.sales import CashMovement, CashSession, Sale, SaleItem
from app.services.numbering import generate_number

RETURN_CONDITIONS = {"resellable", "damaged", "writeoff"}


def q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def q4(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def get_sale(db: Session, sale_id: UUID) -> Sale:
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise NotFoundError("Transaksi tidak ditemukan.", code="SALE_NOT_FOUND")
    return sale


def get_return(db: Session, return_id: UUID) -> Return:
    ret = db.execute(
        select(Return).options(selectinload(Return.items)).where(Return.id == return_id)
    ).scalar_one_or_none()
    if ret is None:
        raise NotFoundError("Retur tidak ditemukan.", code="RETURN_NOT_FOUND")
    return ret


def returned_quantities(db: Session, sale_id: UUID) -> dict[UUID, Decimal]:
    """Total returned quantity per sale item, counting drafts and confirmations."""
    rows = db.execute(
        select(ReturnItem.sale_item_id, func.coalesce(func.sum(ReturnItem.quantity), 0))
        .join(Return, Return.id == ReturnItem.return_id)
        .where(
            Return.sale_id == sale_id,
            Return.status != "cancelled",
            ReturnItem.sale_item_id.is_not(None),
        )
        .group_by(ReturnItem.sale_item_id)
    ).all()
    return {sale_item_id: Decimal(quantity) for sale_item_id, quantity in rows}


def serialize_returnable(db: Session, sale: Sale) -> dict:
    returned = returned_quantities(db, sale.id)
    items = []
    for item in sale.items:
        already = returned.get(item.id, Decimal(0))
        remaining = Decimal(item.quantity) - already
        items.append(
            {
                "id": item.id,
                "sale_item_id": item.id,
                "variant_id": item.variant_id,
                "unit_id": item.unit_id,
                "conversion_factor": item.conversion_factor,
                "quantity": item.quantity,
                "base_quantity": item.base_quantity,
                "condition": "resellable",
                "refund_amount": item.line_total,
                "product_name": item.name_snapshot,
                "sku": item.sku_snapshot,
                "returned_quantity": already,
                "remaining_quantity": remaining,
            }
        )
    return {
        "sale_id": sale.id,
        "number": sale.number,
        "sold_at": sale.sold_at,
        "status": sale.status,
        "customer_id": sale.customer_id,
        "items": items,
    }


def serialize_return(db: Session, ret: Return) -> dict:
    items = []
    for item in ret.items:
        sale_item = db.get(SaleItem, item.sale_item_id) if item.sale_item_id else None
        variant = db.get(ProductVariant, item.variant_id)
        product_name = None
        sku = None
        if sale_item is not None:
            product_name = sale_item.name_snapshot
            sku = sale_item.sku_snapshot
        elif variant is not None:
            product_name = variant.product.name if variant.product else None
            sku = variant.sku
        items.append(
            {
                "id": item.id,
                "sale_item_id": item.sale_item_id,
                "variant_id": item.variant_id,
                "unit_id": item.unit_id,
                "conversion_factor": item.conversion_factor,
                "quantity": item.quantity,
                "base_quantity": item.base_quantity,
                "condition": item.condition,
                "refund_amount": item.refund_amount,
                "product_name": product_name,
                "sku": sku,
            }
        )
    return {
        "id": ret.id,
        "number": ret.number,
        "sale_id": ret.sale_id,
        "purchase_id": ret.purchase_id,
        "type": ret.type,
        "status": ret.status,
        "reason": ret.reason,
        "refund_method": ret.refund_method,
        "refund_amount": ret.refund_amount,
        "created_by": ret.created_by,
        "approved_by": ret.approved_by,
        "created_at": ret.created_at,
        "items": items,
    }


def create_return(db: Session, payload, *, created_by: UUID) -> Return:
    sale = get_sale(db, payload.sale_id)
    if sale.status != "completed":
        raise ConflictError(
            "Hanya transaksi berstatus selesai yang dapat diretur.",
            code="SALE_NOT_RETURNABLE",
        )

    reason = (payload.reason or "").strip()
    if not reason:
        raise BusinessRuleError("Alasan retur wajib diisi.", code="REASON_REQUIRED")
    if not payload.items:
        raise BusinessRuleError("Item retur tidak boleh kosong.", code="EMPTY_RETURN")

    sale_items = {item.id: item for item in sale.items}
    returned = returned_quantities(db, sale.id)
    seen: set[UUID] = set()
    lines: list[dict] = []
    total_refund = Decimal(0)

    for line_in in payload.items:
        if line_in.sale_item_id in seen:
            raise BusinessRuleError(
                "Item retur tidak boleh duplikat.", code="DUPLICATE_RETURN_ITEM"
            )
        seen.add(line_in.sale_item_id)

        sale_item = sale_items.get(line_in.sale_item_id)
        if sale_item is None:
            raise BusinessRuleError(
                "Item penjualan tidak ditemukan pada transaksi ini.",
                code="SALE_ITEM_NOT_FOUND",
            )

        condition = (line_in.condition or "resellable").strip().lower()
        if condition not in RETURN_CONDITIONS:
            raise BusinessRuleError("Kondisi barang tidak valid.", code="INVALID_CONDITION")

        quantity = q4(line_in.quantity)
        if quantity <= 0:
            raise BusinessRuleError(
                "Kuantitas retur harus lebih dari nol.", code="INVALID_QUANTITY"
            )

        already = returned.get(sale_item.id, Decimal(0))
        remaining = Decimal(sale_item.quantity) - already
        if quantity > remaining:
            raise BusinessRuleError(
                f"Kuantitas retur melebihi sisa yang dapat diretur ({remaining:f}).",
                code="QUANTITY_EXCEEDS_RETURNABLE",
            )

        unit_refund = Decimal(sale_item.line_total) / Decimal(sale_item.quantity)
        refund = q2(unit_refund * quantity)
        total_refund += refund

        lines.append(
            {
                "sale_item_id": sale_item.id,
                "variant_id": sale_item.variant_id,
                "unit_id": sale_item.unit_id,
                "conversion_factor": sale_item.conversion_factor,
                "quantity": quantity,
                "base_quantity": q4(quantity * Decimal(sale_item.conversion_factor)),
                "condition": condition,
                "refund_amount": refund,
            }
        )

    ret = Return(
        number=generate_number(db, "RTR"),
        sale_id=sale.id,
        type="sale_return",
        status="draft",
        reason=reason,
        refund_method=payload.refund_method,
        refund_amount=q2(total_refund),
        created_by=created_by,
    )
    db.add(ret)
    db.flush()

    for line in lines:
        db.add(ReturnItem(return_id=ret.id, **line))
    db.flush()
    db.refresh(ret)
    return ret


def confirm_return(db: Session, ret: Return, *, approved_by: UUID) -> Return:
    from app.services import inventory as inventory_service

    if ret.status == "confirmed":
        raise ConflictError("Retur sudah dikonfirmasi.", code="RETURN_ALREADY_CONFIRMED")
    if ret.status != "draft":
        raise ConflictError("Retur tidak dapat dikonfirmasi.", code="RETURN_NOT_DRAFT")

    sale = get_sale(db, ret.sale_id)
    if sale.status != "completed":
        raise ConflictError("Transaksi asal tidak valid untuk retur.", code="SALE_NOT_RETURNABLE")

    for item in ret.items:
        sale_item = db.get(SaleItem, item.sale_item_id) if item.sale_item_id else None
        if sale_item is None:
            raise BusinessRuleError(
                "Item penjualan asal tidak ditemukan.", code="SALE_ITEM_NOT_FOUND"
            )
        if item.condition == "resellable":
            inventory_service.apply_movement(
                db,
                variant_id=item.variant_id,
                location_id=sale.location_id,
                movement_type="sale_return",
                quantity_delta=Decimal(item.base_quantity),
                unit_cost=Decimal(sale_item.cost_unit),
                reference_type="return",
                reference_id=ret.id,
                user_id=approved_by,
                reason=f"Retur {ret.number}",
            )

    if ret.refund_method == "cash" and q2(ret.refund_amount) > 0:
        cash_session = db.get(CashSession, sale.cash_session_id)
        if cash_session is not None and cash_session.status == "open":
            db.add(
                CashMovement(
                    cash_session_id=cash_session.id,
                    type="refund",
                    amount=-q2(ret.refund_amount),
                    reason=f"Retur {ret.number}",
                    reference_type="return",
                    reference_id=ret.id,
                    user_id=approved_by,
                )
            )

    ret.status = "confirmed"
    ret.approved_by = approved_by
    db.flush()
    return ret


def cancel_return(db: Session, ret: Return) -> Return:
    if ret.status == "confirmed":
        raise ConflictError(
            "Retur yang sudah dikonfirmasi tidak dapat dibatalkan.", code="RETURN_ALREADY_CONFIRMED"
        )
    if ret.status == "cancelled":
        raise ConflictError("Retur sudah dibatalkan.", code="RETURN_ALREADY_CANCELLED")
    ret.status = "cancelled"
    db.flush()
    return ret


def return_query():
    return select(Return).options(selectinload(Return.items))
