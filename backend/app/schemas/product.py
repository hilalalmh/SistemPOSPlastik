from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import MoneyStr, ORMModel, QtyStr


class CategoryCreate(BaseModel):
    name: str
    parent_id: UUID | None = None
    is_active: bool = True


class CategoryOut(ORMModel):
    id: UUID
    name: str
    parent_id: UUID | None = None
    is_active: bool


class UnitCreate(BaseModel):
    name: str
    symbol: str
    allows_fraction: bool = False


class UnitOut(ORMModel):
    id: UUID
    name: str
    symbol: str
    allows_fraction: bool


class ConversionIn(BaseModel):
    unit_id: UUID
    base_units_per_unit: Decimal


class ConversionOut(ORMModel):
    id: UUID
    unit_id: UUID
    base_units_per_unit: QtyStr
    is_active: bool


class PriceCreate(BaseModel):
    unit_id: UUID
    min_qty: Decimal = Decimal(0)
    max_qty: Decimal | None = None
    unit_price: Decimal
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class PriceUpdate(BaseModel):
    min_qty: Decimal | None = None
    max_qty: Decimal | None = None
    unit_price: Decimal | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool | None = None


class PriceOut(ORMModel):
    id: UUID
    variant_id: UUID
    unit_id: UUID
    min_qty: QtyStr
    max_qty: QtyStr | None = None
    unit_price: MoneyStr
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool


class ProductCreate(BaseModel):
    name: str
    category_id: UUID | None = None
    brand: str | None = None
    description: str | None = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = None
    category_id: UUID | None = None
    brand: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ProductOut(ORMModel):
    id: UUID
    name: str
    category_id: UUID | None = None
    brand: str | None = None
    description: str | None = None
    is_active: bool


class VariantCreate(BaseModel):
    product_id: UUID
    sku: str
    barcode: str | None = None
    attribute_size: str | None = None
    attribute_color: str | None = None
    attribute_thickness: str | None = None
    attribute_type: str | None = None
    attribute_packaging: str | None = None
    base_unit_id: UUID
    min_stock: Decimal | None = None
    is_active: bool = True
    conversions: list[ConversionIn] = Field(default_factory=list)
    prices: list[PriceCreate] = Field(default_factory=list)


class VariantUpdate(BaseModel):
    sku: str | None = None
    barcode: str | None = None
    attribute_size: str | None = None
    attribute_color: str | None = None
    attribute_thickness: str | None = None
    attribute_type: str | None = None
    attribute_packaging: str | None = None
    base_unit_id: UUID | None = None
    min_stock: Decimal | None = None
    is_active: bool | None = None


class VariantOut(ORMModel):
    id: UUID
    product_id: UUID
    sku: str
    barcode: str | None = None
    attribute_size: str | None = None
    attribute_color: str | None = None
    attribute_thickness: str | None = None
    attribute_type: str | None = None
    attribute_packaging: str | None = None
    base_unit_id: UUID
    min_stock: QtyStr | None = None
    is_active: bool
    product_name: str | None = None


class VariantDetail(VariantOut):
    conversions: list[ConversionOut] = Field(default_factory=list)
    prices: list[PriceOut] = Field(default_factory=list)
    stock_base: QtyStr | None = None
