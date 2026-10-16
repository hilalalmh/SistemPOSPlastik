from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import MoneyStr, ORMModel, QtyStr


class ReturnItemIn(BaseModel):
    sale_item_id: UUID
    quantity: Decimal
    condition: str = "resellable"


class ReturnCreate(BaseModel):
    sale_id: UUID
    reason: str
    refund_method: str | None = None
    items: list[ReturnItemIn] = Field(min_length=1)


class ReturnItemOut(ORMModel):
    id: UUID
    sale_item_id: UUID | None = None
    variant_id: UUID
    unit_id: UUID
    conversion_factor: QtyStr
    quantity: QtyStr
    base_quantity: QtyStr
    condition: str
    refund_amount: MoneyStr
    product_name: str | None = None
    sku: str | None = None


class ReturnOut(ORMModel):
    id: UUID
    number: str
    type: str
    status: str
    sale_id: UUID | None = None
    purchase_id: UUID | None = None
    reason: str
    refund_method: str | None = None
    refund_amount: MoneyStr
    created_by: UUID
    created_by_name: str | None = None
    approved_by: UUID | None = None
    created_at: datetime
    sale_number: str | None = None
    items: list[ReturnItemOut] = []


class ReturnableItemOut(ORMModel):
    id: UUID
    sale_item_id: UUID
    variant_id: UUID
    unit_id: UUID
    conversion_factor: QtyStr
    quantity: QtyStr
    base_quantity: QtyStr
    returned_quantity: QtyStr
    remaining_quantity: QtyStr
    condition: str
    refund_amount: MoneyStr
    product_name: str | None = None
    sku: str | None = None


class ReturnableSaleOut(BaseModel):
    sale_id: UUID
    number: str
    sold_at: datetime
    status: str
    customer_id: UUID | None = None
    items: list[ReturnableItemOut]
