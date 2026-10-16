from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel, QtyStr


class StockBalanceOut(ORMModel):
    variant_id: UUID
    location_id: UUID
    quantity: QtyStr
    avg_cost: QtyStr
    updated_at: datetime
    sku: str | None = None
    product_name: str | None = None
    unit_name: str | None = None
    min_stock: QtyStr | None = None
    low_stock: bool = False


class StockMovementOut(ORMModel):
    id: UUID
    variant_id: UUID
    location_id: UUID
    type: str
    quantity: QtyStr
    unit_cost: QtyStr | None = None
    balance_after: QtyStr
    reference_type: str | None = None
    reference_id: UUID | None = None
    user_id: UUID | None = None
    reason: str | None = None
    created_at: datetime
    product_name: str | None = None


class AdjustmentCreate(BaseModel):
    location_id: UUID | None = None
    variant_id: UUID
    adjustment_type: str
    quantity: Decimal
    reason: str


class AdjustmentOut(ORMModel):
    id: UUID
    number: str
    location_id: UUID
    variant_id: UUID
    adjustment_type: str
    quantity: QtyStr
    reason: str
    created_by: UUID
    created_at: datetime
    balance_after: QtyStr | None = None


class StockCountCreate(BaseModel):
    location_id: UUID | None = None
    notes: str | None = None


class StockCountItemIn(BaseModel):
    variant_id: UUID
    counted_quantity: Decimal
    notes: str | None = None


class StockCountItemsUpdate(BaseModel):
    items: list[StockCountItemIn]


class StockCountItemOut(ORMModel):
    id: UUID
    variant_id: UUID
    system_quantity: QtyStr
    counted_quantity: QtyStr | None = None
    difference: QtyStr | None = None
    unit_id: UUID
    notes: str | None = None
    sku: str | None = None
    product_name: str | None = None


class StockCountOut(ORMModel):
    id: UUID
    number: str
    location_id: UUID
    status: str
    created_by: UUID
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    items: list[StockCountItemOut] = []
