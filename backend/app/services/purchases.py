from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.partner import Supplier
from app.models.product import Product, ProductVariant, Unit
from app.models.purchase import (
    Purchase,
    PurchaseItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
)
from app.services import inventory as inventory_service
from app.services.numbering import generate_number

COST_QUANT = Decimal("0.0001")


def q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def q4(value) -> Decimal:
    return Decimal(value).quantize(COST_QUANT, rounding=ROUND_HALF_UP)


def _recalc_totals(purchase: Purchase, header_discount: Decimal | None = None) -> None:
    subtotal = Decimal(0)
    item_discount = Decimal(0)
    for item in purchase.items:
        gross = q2(Decimal(item.quantity) * Decimal(item.unit_cost))
        discount = q2(item.discount_amount or 0)
        if discount < 0:
            raise BusinessRuleError("Diskon item tidak boleh negatif.", code="INVALID_DISCOUNT")
        if discount > gross:
            raise BusinessRuleError(
                "Diskon item tidak boleh melebihi nilai baris.", code="DISCOUNT_EXCEEDS_LINE"
            )
        item.line_total = q2(gross - discount)
        subtotal += gross
        item_discount += discount

    if header_discount is not None:
        header = q2(header_discount)
        if header < 0:
            raise BusinessRuleError("Diskon tidak boleh negatif.", code="INVALID_DISCOUNT")
        purchase.header_discount = header

    purchase.subtotal = q2(subtotal)
    purchase.discount_total = q2(item_discount + Decimal(purchase.header_discount or 0))
    purchase.total = q2(
        Decimal(purchase.subtotal)
        - Decimal(purchase.discount_total)
        + Decimal(purchase.additional_cost or 0)
    )


def landed_base_costs(purchase: Purchase) -> dict[UUID, Decimal]:
    """Cost per base unit for each item, including allocated additional cost."""
    raw: dict[UUID, Decimal] = {}
    for item in purchase.items:
        raw[item.id] = q2(
            Decimal(item.quantity) * Decimal(item.unit_cost) - Decimal(item.discount_amount or 0)
        )
    sum_raw = sum(raw.values(), Decimal(0))
    additional = Decimal(purchase.additional_cost or 0)
    count = len(purchase.items) or 1

    costs: dict[UUID, Decimal] = {}
    for item in purchase.items:
        share = (additional * raw[item.id] / sum_raw) if sum_raw > 0 else (additional / count)
        landed = raw[item.id] + share
        base_qty = Decimal(item.quantity) * Decimal(item.conversion_factor)
        costs[item.id] = q4(landed / base_qty) if base_qty > 0 else Decimal(0)
    return costs


def _build_items(db: Session, purchase: Purchase, lines: list) -> None:
    for existing in list(purchase.items):
        db.delete(existing)
    purchase.items.clear()
    db.flush()

    for line in lines:
        quantity = Decimal(line.quantity)
        if quantity <= 0:
            raise BusinessRuleError("Kuantitas harus lebih dari nol.", code="INVALID_QUANTITY")
        unit_cost = Decimal(line.unit_cost)
        if unit_cost < 0:
            raise BusinessRuleError("Harga beli tidak boleh negatif.", code="INVALID_PRICE")

        variant = db.get(ProductVariant, line.variant_id)
        if variant is None:
            raise NotFoundError("Varian produk tidak ditemukan.", code="VARIANT_NOT_FOUND")
        unit = db.get(Unit, line.unit_id)
        if unit is None:
            raise NotFoundError("Satuan tidak ditemukan.", code="UNIT_NOT_FOUND")

        factor = _resolve_factor(db, variant, line.unit_id)
        if not unit.allows_fraction and quantity != quantity.to_integral_value():
            raise BusinessRuleError(
                f"Satuan '{unit.name}' tidak mengizinkan kuantitas pecahan.",
                code="FRACTION_NOT_ALLOWED",
            )

        purchase.items.append(
            PurchaseItem(
                variant_id=variant.id,
                unit_id=unit.id,
                conversion_factor=float(factor),
                quantity=float(quantity),
                received_quantity=0,
                unit_cost=float(unit_cost),
                discount_amount=float(q2(line.discount_amount or 0)),
                line_total=0,
            )
        )
    db.flush()


def _resolve_factor(db: Session, variant: ProductVariant, unit_id: UUID) -> Decimal:
    from app.services import pricing

    return pricing.resolve_conversion_factor(db, variant, unit_id)


def create_purchase(
    db: Session,
    payload,
    *,
    location_id: UUID,
    created_by: UUID,
) -> Purchase:
    supplier = db.get(Supplier, payload.supplier_id)
    if supplier is None or not supplier.is_active:
        raise NotFoundError("Supplier tidak ditemukan.", code="SUPPLIER_NOT_FOUND")

    purchase = Purchase(
        number=generate_number(db, "PUR"),
        supplier_id=payload.supplier_id,
        location_id=location_id,
        status="draft",
        invoice_no=payload.invoice_no,
        notes=payload.notes,
        additional_cost=float(q2(payload.additional_cost or 0)),
        created_by=created_by,
    )
    db.add(purchase)
    db.flush()

    _build_items(db, purchase, payload.items)
    _recalc_totals(purchase, payload.discount_amount or 0)

    if payload.order:
        purchase.status = "ordered"
        purchase.ordered_at = datetime.now(UTC)
    db.flush()
    return purchase


def update_purchase(db: Session, purchase: Purchase, payload) -> Purchase:
    if purchase.status != "draft":
        raise ConflictError(
            "Hanya pembelian berstatus draft yang dapat diubah.", code="PURCHASE_NOT_DRAFT"
        )

    if payload.supplier_id is not None and payload.supplier_id != purchase.supplier_id:
        supplier = db.get(Supplier, payload.supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier tidak ditemukan.", code="SUPPLIER_NOT_FOUND")
        purchase.supplier_id = payload.supplier_id

    if payload.invoice_no is not None:
        purchase.invoice_no = payload.invoice_no
    if payload.notes is not None:
        purchase.notes = payload.notes
    if payload.additional_cost is not None:
        purchase.additional_cost = float(q2(payload.additional_cost))
    if payload.items is not None:
        _build_items(db, purchase, payload.items)

    _recalc_totals(purchase, payload.discount_amount)
    db.flush()
    return purchase


def order_purchase(db: Session, purchase: Purchase) -> Purchase:
    if purchase.status != "draft":
        raise ConflictError(
            "Pembelian sudah dipesan atau diproses.", code="PURCHASE_NOT_DRAFT"
        )
    purchase.status = "ordered"
    purchase.ordered_at = datetime.now(UTC)
    db.flush()
    return purchase


def cancel_purchase(db: Session, purchase: Purchase) -> Purchase:
    if purchase.status not in {"draft", "ordered"}:
        raise ConflictError(
            "Pembelian yang sudah diterima tidak dapat dibatalkan.", code="PURCHASE_NOT_CANCELLABLE"
        )
    purchase.status = "cancelled"
    db.flush()
    return purchase


def receive_purchase(
    db: Session,
    purchase: Purchase,
    *,
    lines: list,
    received_by: UUID,
    notes: str | None = None,
) -> PurchaseReceipt:
    if purchase.status in {"cancelled", "received"}:
        raise ConflictError(
            "Pembelian tidak dapat diterima lagi.", code="PURCHASE_NOT_RECEIVABLE"
        )

    item_map = {item.id: item for item in purchase.items}
    for line in lines:
        quantity = Decimal(line.quantity)
        if quantity <= 0:
            raise BusinessRuleError(
                "Jumlah terima harus lebih dari nol.", code="INVALID_QUANTITY"
            )
        item = item_map.get(line.purchase_item_id)
        if item is None:
            raise NotFoundError("Item pembelian tidak ditemukan.", code="ITEM_NOT_FOUND")
        remaining = Decimal(item.quantity) - Decimal(item.received_quantity)
        if quantity > remaining:
            raise BusinessRuleError(
                f"Jumlah terima melebihi sisa pesanan (sisa {q4(remaining)}).",
                code="OVER_RECEIVE",
            )

    costs = landed_base_costs(purchase)
    receipt = PurchaseReceipt(
        number=generate_number(db, "RCV"),
        purchase_id=purchase.id,
        received_by=received_by,
        received_at=datetime.now(UTC),
        notes=notes,
    )
    db.add(receipt)
    db.flush()

    for line in lines:
        item = item_map[line.purchase_item_id]
        received_qty = Decimal(line.quantity)
        base_qty = q4(received_qty * Decimal(item.conversion_factor))
        unit_cost = costs[item.id]

        inventory_service.apply_movement(
            db,
            variant_id=item.variant_id,
            location_id=purchase.location_id,
            movement_type="purchase",
            quantity_delta=base_qty,
            unit_cost=unit_cost,
            reference_type="purchase_receipt",
            reference_id=receipt.id,
            user_id=received_by,
            reason=f"Penerimaan {purchase.number}",
        )

        item.received_quantity = float(Decimal(item.received_quantity) + received_qty)
        item.base_quantity = float(Decimal(item.base_quantity or 0) + base_qty)
        db.add(
            PurchaseReceiptItem(
                receipt_id=receipt.id,
                purchase_item_id=item.id,
                base_quantity=float(base_qty),
                unit_cost=float(unit_cost),
            )
        )

    fully_received = all(
        Decimal(item.received_quantity) >= Decimal(item.quantity) for item in purchase.items
    )
    purchase.status = "received" if fully_received else "partially_received"
    purchase.received_by = received_by
    purchase.received_at = datetime.now(UTC)
    db.flush()
    return receipt


def get_purchase(db: Session, purchase_id: UUID) -> Purchase:
    purchase = db.execute(
        select(Purchase)
        .options(selectinload(Purchase.items))
        .where(Purchase.id == purchase_id)
    ).scalar_one_or_none()
    if purchase is None:
        raise NotFoundError("Pembelian tidak ditemukan.", code="PURCHASE_NOT_FOUND")
    return purchase


def list_receipts(db: Session, purchase_id: UUID) -> list[PurchaseReceipt]:
    return (
        db.execute(
            select(PurchaseReceipt)
            .where(PurchaseReceipt.purchase_id == purchase_id)
            .options(selectinload(PurchaseReceipt.items))
            .order_by(PurchaseReceipt.received_at.desc())
        )
        .scalars()
        .all()
    )


def serialize_purchase(db: Session, purchase: Purchase) -> dict:
    costs = landed_base_costs(purchase)
    items = []
    for item in purchase.items:
        variant = db.get(ProductVariant, item.variant_id)
        product = db.get(Product, variant.product_id) if variant else None
        quantity = Decimal(item.quantity)
        received = Decimal(item.received_quantity)
        items.append(
            {
                "id": item.id,
                "variant_id": item.variant_id,
                "unit_id": item.unit_id,
                "conversion_factor": item.conversion_factor,
                "quantity": item.quantity,
                "received_quantity": item.received_quantity,
                "base_quantity": item.base_quantity,
                "unit_cost": item.unit_cost,
                "discount_amount": item.discount_amount,
                "line_total": item.line_total,
                "remaining_quantity": q4(quantity - received),
                "base_unit_cost": costs.get(item.id, Decimal(0)),
                "product_name": product.name if product else None,
                "sku": variant.sku if variant else None,
            }
        )

    supplier = db.get(Supplier, purchase.supplier_id)
    receipts = [
        {
            "id": receipt.id,
            "number": receipt.number,
            "received_by": receipt.received_by,
            "received_at": receipt.received_at,
            "notes": receipt.notes,
            "items": [
                {
                    "id": ri.id,
                    "purchase_item_id": ri.purchase_item_id,
                    "base_quantity": ri.base_quantity,
                    "unit_cost": ri.unit_cost,
                }
                for ri in receipt.items
            ],
        }
        for receipt in purchase_receipts(db, purchase.id)
    ]

    return {
        "id": purchase.id,
        "number": purchase.number,
        "supplier_id": purchase.supplier_id,
        "supplier_name": supplier.name if supplier else None,
        "location_id": purchase.location_id,
        "status": purchase.status,
        "subtotal": purchase.subtotal,
        "discount_total": purchase.discount_total,
        "additional_cost": purchase.additional_cost,
        "total": purchase.total,
        "invoice_no": purchase.invoice_no,
        "notes": purchase.notes,
        "created_by": purchase.created_by,
        "received_by": purchase.received_by,
        "created_at": purchase.created_at,
        "ordered_at": purchase.ordered_at,
        "received_at": purchase.received_at,
        "items": items,
        "receipts": receipts,
    }


def purchase_receipts(db: Session, purchase_id: UUID) -> list[PurchaseReceipt]:
    return (
        db.execute(
            select(PurchaseReceipt)
            .options(selectinload(PurchaseReceipt.items))
            .where(PurchaseReceipt.purchase_id == purchase_id)
            .order_by(PurchaseReceipt.received_at)
        )
        .scalars()
        .all()
    )


def purchase_query():
    return select(Purchase).options(selectinload(Purchase.items))
