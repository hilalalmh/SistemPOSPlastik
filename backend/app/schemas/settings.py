from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class StoreSettingOut(ORMModel):
    id: UUID
    store_name: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    logo_url: str | None = None
    receipt_header: str | None = None
    receipt_footer: str | None = None
    timezone: str
    currency: str
    invoice_prefix_sale: str
    invoice_prefix_purchase: str
    invoice_prefix_return: str
    discount_max_percent_cashier: Decimal
    allow_negative_stock: bool


class StoreSettingUpdate(BaseModel):
    store_name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    logo_url: str | None = None
    receipt_header: str | None = None
    receipt_footer: str | None = None
    timezone: str | None = None
    invoice_prefix_sale: str | None = None
    invoice_prefix_purchase: str | None = None
    invoice_prefix_return: str | None = None
    discount_max_percent_cashier: Decimal | None = None
    allow_negative_stock: bool | None = None


class LocationOut(ORMModel):
    id: UUID
    name: str
    code: str
    is_default: bool
    is_active: bool


class LocationCreate(BaseModel):
    name: str
    code: str
    is_default: bool = False
