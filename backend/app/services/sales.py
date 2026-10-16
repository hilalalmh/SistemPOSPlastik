from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError
from app.models.inventory import StockBalance
from app.models.product import ProductVariant, Unit
from app.models.sales import CashMovement, CashSession, Payment, Sale, SaleItem
from app.models.store import Location, StoreSetting
from app.services.numbering import generate_number


def q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def q4(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


@dataclass
class CartItemInput:
    variant_id: UUID
    unit_id: UUID
    quantity: Decimal
    discount_amount: Decimal = Decimal(0)
    unit_price_override: Decimal | None = None


@dataclass
class CartLine:
    variant: ProductVariant
    unit: Unit
    conversion_factor: Decimal
    quantity: Decimal
    base_quantity: Decimal
    unit_price: Decimal
    min_qty: Decimal
    max_qty: Decimal | None
    discount_amount: Decimal
    line_total: Decimal
    cost_unit: Decimal
    cost_total: Decimal
    stock_base: Decimal
    stock_sufficient: bool
    price_overridden: bool = False


@dataclass
class CartComputation:
    lines: list[CartLine] = field(default_factory=list)
    subtotal: Decimal = Decimal(0)
    discount_total: Decimal = Decimal(0)
    tax_total: Decimal = Decimal(0)
    total: Decimal = Decimal(0)
    cost_total: Decimal = Decimal(0)


def get_default_location_id(db: Session) -> UUID:
    location = db.execute(
        select(Location).where(Location.is_default.is_(True)).limit(1)
    ).scalar_one_or_none()
    if location is None:
        location = db.execute(select(Location).limit(1)).scalar_one_or_none()
    if location is None:
        raise BusinessRuleError("Lokasi toko belum dikonfigurasi.", code="LOCATION_MISSING")
    return location.id


def _load_balance(
    db: Session, variant_id: UUID, location_id: UUID, *, lock: bool
) -> StockBalance | None:
    stmt = select(StockBalance).where(
        StockBalance.variant_id == variant_id,
        StockBalance.location_id == location_id,
    )
    if lock:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def compute_cart(
    db: Session,
    items: list[CartItemInput],
    location_id: UUID,
    *,
    lock: bool = False,
    allow_price_override: bool = False,
) -> CartComputation:
    """Compute a cart server-side.

    The frontend is never trusted for prices, discounts, or totals
    (production.md Bagian 5 butir 5).
    """
    if not items:
        raise BusinessRuleError("Keranjang tidak boleh kosong.", code="EMPTY_CART")

    from app.services import pricing  # local import to avoid cycles

    result = CartComputation()
    subtotal = Decimal(0)
    discount_total = Decimal(0)
    cost_total = Decimal(0)
    seen: dict[UUID, Decimal] = {}

    for item in items:
        quantity = Decimal(item.quantity)
        if quantity <= 0:
            raise BusinessRuleError("Kuantitas harus lebih dari nol.", code="INVALID_QUANTITY")

        variant = db.get(ProductVariant, item.variant_id)
        if variant is None:
            raise BusinessRuleError("Varian produk tidak ditemukan.", code="VARIANT_NOT_FOUND")
        if not variant.is_active or not variant.product.is_active:
            raise BusinessRuleError(
                f"Produk '{variant.product.name}' tidak aktif dan tidak dapat dijual.",
                code="PRODUCT_INACTIVE",
            )

        unit = db.get(Unit, item.unit_id)
        if unit is None:
            raise BusinessRuleError("Satuan tidak ditemukan.", code="UNIT_NOT_FOUND")
        if not unit.allows_fraction and quantity != quantity.to_integral_value():
            raise BusinessRuleError(
                f"Satuan '{unit.name}' tidak mengizinkan kuantitas pecahan.",
                code="FRACTION_NOT_ALLOWED",
            )

        factor = pricing.resolve_conversion_factor(db, variant, item.unit_id)

        if item.unit_price_override is not None:
            if not allow_price_override:
                raise BusinessRuleError(
                    "Anda tidak memiliki izin mengubah harga pada transaksi.",
                    code="PRICE_OVERRIDE_FORBIDDEN",
                )
            unit_price = Decimal(item.unit_price_override)
            if unit_price < 0:
                raise BusinessRuleError("Harga tidak boleh negatif.", code="INVALID_PRICE")
            min_qty, max_qty = Decimal(0), None
            price_overridden = True
        else:
            resolved = pricing.resolve_price(db, item.variant_id, item.unit_id, quantity)
            unit_price = Decimal(resolved.unit_price)
            min_qty, max_qty = resolved.min_qty, resolved.max_qty
            price_overridden = False

        gross = q2(quantity * unit_price)
        discount = q2(item.discount_amount or 0)
        if discount < 0:
            raise BusinessRuleError("Diskon tidak boleh negatif.", code="INVALID_DISCOUNT")
        if discount > gross:
            raise BusinessRuleError(
                "Diskon tidak boleh melebihi nilai baris.", code="DISCOUNT_EXCEEDS_LINE"
            )
        line_total = q2(gross - discount)

        balance = _load_balance(db, item.variant_id, location_id, lock=lock)
        stock_base = Decimal(balance.quantity) if balance else Decimal(0)
        avg_cost = Decimal(balance.avg_cost) if balance else Decimal(0)
        base_quantity = q4(quantity * factor)

        already = seen.get(item.variant_id, Decimal(0))
        available = stock_base - already
        seen[item.variant_id] = already + base_quantity
        stock_sufficient = available >= base_quantity

        line = CartLine(
            variant=variant,
            unit=unit,
            conversion_factor=factor,
            quantity=quantity,
            base_quantity=base_quantity,
            unit_price=unit_price,
            min_qty=min_qty,
            max_qty=max_qty,
            discount_amount=discount,
            line_total=line_total,
            cost_unit=avg_cost,
            cost_total=q2(base_quantity * avg_cost),
            stock_base=stock_base,
            stock_sufficient=stock_sufficient,
            price_overridden=price_overridden,
        )
        result.lines.append(line)
        subtotal += gross
        discount_total += discount
        cost_total += line.cost_total

    result.subtotal = q2(subtotal)
    result.discount_total = q2(discount_total)
    result.tax_total = Decimal("0.00")
    result.total = q2(subtotal - discount_total)
    result.cost_total = q2(cost_total)
    return result


def _enforce_discount(db: Session, cart: CartComputation, override: bool) -> None:
    setting = db.execute(select(StoreSetting).limit(1)).scalar_one_or_none()
    limit = Decimal(setting.discount_max_percent_cashier) if setting else Decimal(0)
    if cart.subtotal == 0:
        return
    percent = (cart.discount_total / cart.subtotal) * Decimal(100)
    if not override and percent > limit:
        raise BusinessRuleError(
            f"Diskon {percent:.2f}% melebihi batas {limit:.2f}%. Perlu izin tambahan.",
            code="DISCOUNT_LIMIT_EXCEEDED",
        )


def checkout(
    db: Session,
    *,
    cash_session: CashSession,
    items: list[CartItemInput],
    payments: list[dict],
    location_id: UUID,
    cashier_id: UUID,
    customer_id: UUID | None = None,
    notes: str | None = None,
    idempotency_key: str | None = None,
    allow_price_override: bool = False,
    discount_override: bool = False,
) -> Sale:
    """Persist a sale with items, payments, and stock movements atomically.

    A sale never exists without matching stock movements
    (production.md Bagian 5 butir 3).
    """
    from app.services import inventory as inventory_service

    cart = compute_cart(
        db, items, location_id, lock=True, allow_price_override=allow_price_override
    )

    for line in cart.lines:
        if not line.stock_sufficient:
            raise BusinessRuleError(
                f"Stok '{line.variant.product.name}' tidak mencukupi. "
                f"Tersedia {line.stock_base} satuan dasar.",
                code="INSUFFICIENT_STOCK",
            )

    _enforce_discount(db, cart, discount_override)

    total = cart.total
    paid_total = q2(sum(Decimal(str(p["amount"])) for p in payments))
    if paid_total < total:
        raise BusinessRuleError(
            "Total pembayaran kurang dari total transaksi.", code="PAYMENT_INSUFFICIENT"
        )
    cash_paid = q2(sum(Decimal(str(p["amount"])) for p in payments if p["method"] == "cash"))
    change_total = q2(max(cash_paid - total, Decimal(0)))

    number = generate_number(db, "SLS")
    sale = Sale(
        number=number,
        location_id=location_id,
        cashier_id=cashier_id,
        cash_session_id=cash_session.id,
        customer_id=customer_id,
        status="completed",
        subtotal=cart.subtotal,
        discount_total=cart.discount_total,
        tax_total=cart.tax_total,
        total=cart.total,
        paid_total=paid_total,
        change_total=change_total,
        cost_total=cart.cost_total,
        notes=notes,
        sold_at=datetime.now(UTC),
        idempotency_key=idempotency_key,
    )
    db.add(sale)
    db.flush()

    for line in cart.lines:
        db.add(
            SaleItem(
                sale_id=sale.id,
                variant_id=line.variant.id,
                name_snapshot=line.variant.product.name,
                sku_snapshot=line.variant.sku,
                unit_id=line.unit.id,
                unit_name_snapshot=line.unit.name,
                conversion_factor=line.conversion_factor,
                quantity=line.quantity,
                base_quantity=line.base_quantity,
                unit_price=line.unit_price,
                discount_amount=line.discount_amount,
                line_total=line.line_total,
                cost_unit=line.cost_unit,
                cost_total=line.cost_total,
            )
        )
        inventory_service.apply_movement(
            db,
            variant_id=line.variant.id,
            location_id=location_id,
            movement_type="sale",
            quantity_delta=-line.base_quantity,
            reference_type="sale",
            reference_id=sale.id,
            user_id=cashier_id,
        )

    for p in payments:
        db.add(
            Payment(
                sale_id=sale.id,
                method=p["method"],
                amount=q2(p["amount"]),
                status="confirmed",
                reference_no=p.get("reference_no"),
                paid_at=datetime.now(UTC),
            )
        )

    cash_to_drawer = q2(cash_paid - change_total)
    if cash_to_drawer > 0:
        db.add(
            CashMovement(
                cash_session_id=cash_session.id,
                type="sale_cash",
                amount=cash_to_drawer,
                reason=f"Penjualan {sale.number}",
                reference_type="sale",
                reference_id=sale.id,
                user_id=cashier_id,
            )
        )

    db.flush()
    return sale


def get_open_session(db: Session, cashier_id: UUID, location_id: UUID) -> CashSession | None:
    return db.execute(
        select(CashSession).where(
            CashSession.cashier_id == cashier_id,
            CashSession.location_id == location_id,
            CashSession.status == "open",
        )
    ).scalar_one_or_none()


def open_cash_session(
    db: Session, *, cashier_id: UUID, location_id: UUID, opening_cash, user_id: UUID
) -> CashSession:
    if get_open_session(db, cashier_id, location_id) is not None:
        raise ConflictError("Anda masih memiliki shift yang terbuka.", code="SESSION_ALREADY_OPEN")

    session = CashSession(
        location_id=location_id,
        cashier_id=cashier_id,
        opening_cash=q2(opening_cash),
        status="open",
        opened_at=datetime.now(UTC),
    )
    db.add(session)
    db.flush()
    db.add(
        CashMovement(
            cash_session_id=session.id,
            type="opening",
            amount=q2(opening_cash),
            reason="Kas awal shift",
            user_id=user_id,
        )
    )
    db.flush()
    return session


def expected_cash(db: Session, session: CashSession) -> Decimal:
    movements = (
        db.execute(select(CashMovement).where(CashMovement.cash_session_id == session.id))
        .scalars()
        .all()
    )
    total = sum((Decimal(m.amount) for m in movements), Decimal(0))
    return q2(total)


def close_cash_session(
    db: Session,
    session: CashSession,
    *,
    counted_cash,
    closed_by: UUID,
    notes: str | None = None,
) -> CashSession:
    if session.status != "open":
        raise ConflictError("Shift sudah ditutup.", code="SESSION_NOT_OPEN")

    expected = expected_cash(db, session)
    counted = q2(counted_cash)
    session.expected_cash = expected
    session.counted_cash = counted
    session.difference = q2(counted - expected)
    session.status = "closed"
    session.closed_at = datetime.now(UTC)
    session.closed_by = closed_by
    if notes:
        session.notes = notes
    db.flush()
    return session


def add_cash_movement(
    db: Session,
    session: CashSession,
    *,
    movement_type: str,
    amount,
    reason: str,
    user_id: UUID,
) -> CashMovement:
    if session.status != "open":
        raise ConflictError("Shift tidak dalam status terbuka.", code="SESSION_NOT_OPEN")
    if movement_type not in {"cash_in", "cash_out"}:
        raise BusinessRuleError("Jenis pergerakan kas tidak valid.", code="INVALID_CASH_MOVEMENT")
    value = q2(amount)
    if movement_type == "cash_out":
        value = -value
    movement = CashMovement(
        cash_session_id=session.id,
        type=movement_type,
        amount=value,
        reason=reason,
        user_id=user_id,
    )
    db.add(movement)
    db.flush()
    return movement
