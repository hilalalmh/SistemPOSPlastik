from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import MoneyStr, QtyStr


class PaymentBreakdown(BaseModel):
    method: str
    amount: MoneyStr
    count: int


class DashboardOut(BaseModel):
    date: str
    sales_count: int
    gross_revenue: MoneyStr
    net_revenue: MoneyStr
    discount_total: MoneyStr
    payment_breakdown: list[PaymentBreakdown]
    low_stock_count: int


class SalesSummaryRow(BaseModel):
    period: str
    sales_count: int
    gross_revenue: MoneyStr
    discount_total: MoneyStr
    net_revenue: MoneyStr
    cost_total: MoneyStr
    gross_profit: MoneyStr


class SalesReportOut(BaseModel):
    from_date: date
    to_date: date
    rows: list[SalesSummaryRow]
    totals: SalesSummaryRow


class TopProductRow(BaseModel):
    variant_id: UUID
    product_name: str
    sku: str
    quantity_sold: QtyStr
    revenue: MoneyStr


class StockReportRow(BaseModel):
    variant_id: UUID
    product_name: str
    sku: str
    unit_name: str
    quantity: QtyStr
    avg_cost: QtyStr
    stock_value: MoneyStr
    min_stock: QtyStr | None = None
    low_stock: bool = False
