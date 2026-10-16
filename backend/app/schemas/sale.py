from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import MoneyStr, ORMModel, QtyStr


class CartItemIn(BaseModel):
    variant_id: UUID
    unit_id: UUID
    quantity: Decimal
    discount_amount: Decimal = Decimal(0)
    unit_price_override: Decimal | None = None


class QuoteRequest(BaseModel):
    items: list[CartItemIn]
    location_id: UUID | None = None


class QuoteLineOut(BaseModel):
    variant_id: UUID
    name: str
    sku: str
    unit_id: UUID
    unit_name: str
    conversion_factor: QtyStr
    quantity: QtyStr
    base_quantity: QtyStr
    unit_price: MoneyStr
    min_qty: QtyStr
    max_qty: QtyStr | None = None
    discount_amount: MoneyStr
    line_total: MoneyStr
    stock_base: QtyStr
    stock_sufficient: bool
    price_overridden: bool = False


class QuoteResponse(BaseModel):
    items: list[QuoteLineOut]
    subtotal: MoneyStr
    discount_total: MoneyStr
    tax_total: MoneyStr
    total: MoneyStr


class PaymentIn(BaseModel):
    method: str
    amount: Decimal
    reference_no: str | None = None


class CheckoutRequest(BaseModel):
    cash_session_id: UUID
    items: list[CartItemIn]
    payments: list[PaymentIn]
    location_id: UUID | None = None
    customer_id: UUID | None = None
    notes: str | None = None


class PaymentOut(ORMModel):
    method: str
    amount: MoneyStr
    status: str
    reference_no: str | None = None


class SaleItemOut(ORMModel):
    variant_id: UUID
    name_snapshot: str
    sku_snapshot: str
    unit_name_snapshot: str
    conversion_factor: QtyStr
    quantity: QtyStr
    base_quantity: QtyStr
    unit_price: MoneyStr
    discount_amount: MoneyStr
    line_total: MoneyStr
    cost_unit: QtyStr
    cost_total: MoneyStr


class SaleOut(ORMModel):
    id: UUID
    number: str
    status: str
    cashier_id: UUID
    cash_session_id: UUID
    customer_id: UUID | None = None
    subtotal: MoneyStr
    discount_total: MoneyStr
    tax_total: MoneyStr
    total: MoneyStr
    paid_total: MoneyStr
    change_total: MoneyStr
    cost_total: MoneyStr
    notes: str | None = None
    sold_at: datetime
    voided_at: datetime | None = None
    void_reason: str | None = None
    items: list[SaleItemOut] = []
    payments: list[PaymentOut] = []


class VoidRequest(BaseModel):
    reason: str


class ReceiptOut(BaseModel):
    store_name: str
    store_address: str | None = None
    store_phone: str | None = None
    receipt_header: str | None = None
    receipt_footer: str | None = None
    number: str
    sold_at: datetime
    cashier_name: str
    items: list[dict]
    subtotal: MoneyStr
    discount_total: MoneyStr
    total: MoneyStr
    paid_total: MoneyStr
    change_total: MoneyStr
    payments: list[PaymentOut]


class CashSessionOpen(BaseModel):
    location_id: UUID | None = None
    opening_cash: Decimal = Decimal(0)


class CashSessionClose(BaseModel):
    counted_cash: Decimal
    notes: str | None = None


class CashMovementCreate(BaseModel):
    type: str
    amount: Decimal
    reason: str


class CashMovementOut(ORMModel):
    id: UUID
    type: str
    amount: MoneyStr
    reason: str | None = None
    created_at: datetime


class CashSessionOut(ORMModel):
    id: UUID
    location_id: UUID
    cashier_id: UUID
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: MoneyStr
    expected_cash: MoneyStr | None = None
    counted_cash: MoneyStr | None = None
    difference: MoneyStr | None = None
    status: str
    notes: str | None = None
    movements: list[CashMovementOut] = []
    sales_count: int = 0
    sales_total: MoneyStr = Decimal(0)


class CatalogItemOut(BaseModel):
    variant_id: UUID
    product_name: str
    sku: str
    barcode: str | None = None
    attributes: dict
    base_unit_id: UUID
    base_unit_name: str
    stock_base: QtyStr
    price_from: MoneyStr | None = None
    units: list[dict] = Field(default_factory=list)
