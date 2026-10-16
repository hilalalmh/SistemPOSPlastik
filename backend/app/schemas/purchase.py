from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import MoneyStr, ORMModel, QtyStr


class PurchaseItemIn(BaseModel):
    variant_id: UUID
    unit_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    discount_amount: Decimal = Decimal(0)


class PurchaseCreate(BaseModel):
    supplier_id: UUID
    location_id: UUID | None = None
    invoice_no: str | None = None
    notes: str | None = None
    discount_amount: Decimal = Decimal(0)
    additional_cost: Decimal = Decimal(0)
    items: list[PurchaseItemIn] = Field(min_length=1)
    order: bool = False


class PurchaseUpdate(BaseModel):
    supplier_id: UUID | None = None
    invoice_no: str | None = None
    notes: str | None = None
    discount_amount: Decimal | None = None
    additional_cost: Decimal | None = None
    items: list[PurchaseItemIn] | None = None


class ReceiveItemIn(BaseModel):
    purchase_item_id: UUID
    quantity: Decimal


class ReceiveRequest(BaseModel):
    items: list[ReceiveItemIn] = Field(min_length=1)
    notes: str | None = None


class PurchaseItemOut(ORMModel):
    id: UUID
    variant_id: UUID
    unit_id: UUID
    conversion_factor: QtyStr
    quantity: QtyStr
    received_quantity: QtyStr
    base_quantity: QtyStr | None = None
    unit_cost: MoneyStr
    discount_amount: MoneyStr
    line_total: MoneyStr
    remaining_quantity: QtyStr
    base_unit_cost: QtyStr
    product_name: str | None = None
    sku: str | None = None


class PurchaseReceiptItemOut(ORMModel):
    id: UUID
    purchase_item_id: UUID
    base_quantity: QtyStr
    unit_cost: QtyStr


class PurchaseReceiptOut(ORMModel):
    id: UUID
    number: str
    received_by: UUID
    received_at: datetime
    notes: str | None = None
    items: list[PurchaseReceiptItemOut] = []


class PurchaseOut(ORMModel):
    id: UUID
    number: str
    supplier_id: UUID
    supplier_name: str | None = None
    location_id: UUID
    status: str
    subtotal: MoneyStr
    discount_total: MoneyStr
    additional_cost: MoneyStr
    total: MoneyStr
    invoice_no: str | None = None
    notes: str | None = None
    created_by: UUID
    received_by: UUID | None = None
    created_at: datetime
    ordered_at: datetime | None = None
    received_at: datetime | None = None
    items: list[PurchaseItemOut] = []
    receipts: list[PurchaseReceiptOut] = []
