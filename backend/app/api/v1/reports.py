from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.timeutil import day_bounds as _day_bounds
from app.core.timeutil import tz as _tz
from app.models.expense import Expense, ExpenseCategory
from app.models.inventory import StockBalance
from app.models.partner import Supplier
from app.models.product import ProductVariant, Unit
from app.models.purchase import Purchase
from app.models.return_ import Return
from app.models.sales import Payment, Sale, SaleItem
from app.models.user import User
from app.permissions import (
    REPORT_DASHBOARD,
    REPORT_EXPENSE,
    REPORT_PROFIT,
    REPORT_PURCHASE,
    REPORT_SALES,
    REPORT_STOCK,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard")
def dashboard(
    target: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_DASHBOARD)),
):
    day = date.fromisoformat(target) if target else datetime.now(_tz()).date()
    start, end = _day_bounds(day)

    base = select(Sale).where(Sale.status == "completed", Sale.sold_at >= start, Sale.sold_at < end)
    sub = base.subquery()
    row = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(sub.c.subtotal), 0),
            func.coalesce(func.sum(sub.c.total), 0),
            func.coalesce(func.sum(sub.c.discount_total), 0),
        ).select_from(sub)
    ).one()

    payment_rows = db.execute(
        select(Payment.method, func.coalesce(func.sum(Payment.amount), 0), func.count())
        .join(Sale, Sale.id == Payment.sale_id)
        .where(Sale.status == "completed", Sale.sold_at >= start, Sale.sold_at < end)
        .group_by(Payment.method)
    ).all()
    change_total = Decimal(
        db.execute(
            select(func.coalesce(func.sum(Sale.change_total), 0)).where(
                Sale.status == "completed", Sale.sold_at >= start, Sale.sold_at < end
            )
        ).scalar_one()
    )
    payment_breakdown = [
        {
            "method": method,
            "amount": str(Decimal(amount) - (change_total if method == "cash" else Decimal(0))),
            "count": count,
        }
        for method, amount, count in payment_rows
    ]

    low_stock_count = _low_stock_count(db)

    return_total = _return_total(db, start, end)
    net_revenue = Decimal(row[2])
    return {
        "date": day.isoformat(),
        "sales_count": row[0],
        "gross_revenue": str(row[1]),
        "return_total": str(return_total),
        "net_revenue": str(row[2]),
        "net_after_return": str(net_revenue - return_total),
        "discount_total": str(row[3]),
        "payment_breakdown": payment_breakdown,
        "low_stock_count": low_stock_count,
    }


def _return_total(db: Session, start: datetime, end: datetime) -> Decimal:
    total = db.execute(
        select(func.coalesce(func.sum(Return.refund_amount), 0)).where(
            Return.type == "sale_return",
            Return.status == "confirmed",
            Return.created_at >= start,
            Return.created_at < end,
        )
    ).scalar_one()
    return Decimal(total)


def _low_stock_count(db: Session) -> int:
    rows = db.execute(
        select(StockBalance.quantity, ProductVariant.min_stock).join(
            ProductVariant, ProductVariant.id == StockBalance.variant_id
        )
    ).all()
    return sum(
        1 for qty, min_stock in rows if min_stock is not None and Decimal(qty) < Decimal(min_stock)
    )


@router.get("/sales")
def sales_report(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    group_by: str = Query("day"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_SALES)),
):
    tz = _tz()
    today = datetime.now(tz).date()
    start_day = date.fromisoformat(date_from) if date_from else today
    end_day = date.fromisoformat(date_to) if date_to else today
    start, _ = _day_bounds(start_day)
    _, end = _day_bounds(end_day)

    rows = (
        db.execute(
            select(Sale).where(
                Sale.status == "completed", Sale.sold_at >= start, Sale.sold_at < end
            )
        )
        .scalars()
        .all()
    )

    buckets: dict[str, dict] = {}
    for sale in rows:
        local = sale.sold_at.astimezone(tz)
        if group_by == "month":
            key = local.strftime("%Y-%m")
        elif group_by == "week":
            key = f"{local.isocalendar().year}-W{local.isocalendar().week:02d}"
        else:
            key = local.strftime("%Y-%m-%d")
        bucket = buckets.setdefault(
            key,
            {
                "period": key,
                "sales_count": 0,
                "gross": Decimal(0),
                "discount": Decimal(0),
                "net": Decimal(0),
                "cost": Decimal(0),
                "returns": Decimal(0),
            },
        )
        bucket["sales_count"] += 1
        bucket["gross"] += Decimal(sale.subtotal)
        bucket["discount"] += Decimal(sale.discount_total)
        bucket["net"] += Decimal(sale.total)
        bucket["cost"] += Decimal(sale.cost_total)

    returns = (
        db.execute(
            select(Return).where(
                Return.type == "sale_return",
                Return.status == "confirmed",
                Return.created_at >= start,
                Return.created_at < end,
            )
        )
        .scalars()
        .all()
    )
    for ret in returns:
        local = ret.created_at.astimezone(tz)
        if group_by == "month":
            key = local.strftime("%Y-%m")
        elif group_by == "week":
            key = f"{local.isocalendar().year}-W{local.isocalendar().week:02d}"
        else:
            key = local.strftime("%Y-%m-%d")
        bucket = buckets.setdefault(
            key,
            {
                "period": key,
                "sales_count": 0,
                "gross": Decimal(0),
                "discount": Decimal(0),
                "net": Decimal(0),
                "cost": Decimal(0),
                "returns": Decimal(0),
            },
        )
        bucket["returns"] += Decimal(ret.refund_amount)

    summary = []
    totals = {
        "period": "TOTAL",
        "sales_count": 0,
        "gross": Decimal(0),
        "discount": Decimal(0),
        "net": Decimal(0),
        "cost": Decimal(0),
        "returns": Decimal(0),
    }
    for key in sorted(buckets):
        bucket = buckets[key]
        totals["sales_count"] += bucket["sales_count"]
        totals["gross"] += bucket["gross"]
        totals["discount"] += bucket["discount"]
        totals["net"] += bucket["net"]
        totals["cost"] += bucket["cost"]
        totals["returns"] += bucket["returns"]
        summary.append(_row_out(bucket))
    return {
        "from_date": start_day.isoformat(),
        "to_date": end_day.isoformat(),
        "rows": summary,
        "totals": _row_out(totals),
    }


def _row_out(bucket: dict) -> dict:
    gross_profit = bucket["net"] - bucket["cost"]
    return {
        "period": bucket["period"],
        "sales_count": bucket["sales_count"],
        "gross_revenue": str(bucket["gross"]),
        "discount_total": str(bucket["discount"]),
        "return_total": str(bucket["returns"]),
        "net_revenue": str(bucket["net"]),
        "net_after_return": str(bucket["net"] - bucket["returns"]),
        "cost_total": str(bucket["cost"]),
        "gross_profit": str(gross_profit),
    }


def _top_products(
    db: Session, start: datetime, end: datetime, *, by: str, limit: int
) -> list[dict]:
    order_col = (
        func.sum(SaleItem.base_quantity) if by == "quantity" else func.sum(SaleItem.line_total)
    )
    rows = db.execute(
        select(
            SaleItem.variant_id,
            func.sum(SaleItem.base_quantity),
            func.sum(SaleItem.line_total),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.status == "completed", Sale.sold_at >= start, Sale.sold_at < end)
        .group_by(SaleItem.variant_id)
        .order_by(order_col.desc())
        .limit(limit)
    ).all()

    data = []
    for variant_id, qty, revenue in rows:
        variant = db.get(ProductVariant, variant_id)
        data.append(
            {
                "variant_id": str(variant_id),
                "product_name": variant.product.name if variant else None,
                "sku": variant.sku if variant else None,
                "quantity_sold": str(qty),
                "revenue": str(revenue),
            }
        )
    return data


def _top_products_range(date_from: str | None, date_to: str | None) -> tuple[datetime, datetime]:
    tz = _tz()
    today = datetime.now(tz).date()
    start_day = date.fromisoformat(date_from) if date_from else today - timedelta(days=30)
    end_day = date.fromisoformat(date_to) if date_to else today
    start, _ = _day_bounds(start_day)
    _, end = _day_bounds(end_day)
    return start, end


@router.get("/top-products")
def top_products(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    by: str = Query("value", pattern="^(quantity|value)$"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_SALES)),
):
    start, end = _top_products_range(date_from, date_to)
    return {"data": _top_products(db, start, end, by=by, limit=limit)}


@router.get("/products/top")
def products_top(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    by: str = Query("value", pattern="^(quantity|value)$"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_SALES)),
):
    start, end = _top_products_range(date_from, date_to)
    return {"data": _top_products(db, start, end, by=by, limit=limit)}


@router.get("/stock")
def stock_report(
    low_stock: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_STOCK)),
):
    rows = (
        db.execute(
            select(StockBalance).join(ProductVariant, ProductVariant.id == StockBalance.variant_id)
        )
        .scalars()
        .all()
    )
    data = []
    total_value = Decimal(0)
    for balance in rows:
        variant = db.get(ProductVariant, balance.variant_id)
        unit = db.get(Unit, variant.base_unit_id) if variant else None
        stock_value = Decimal(balance.quantity) * Decimal(balance.avg_cost)
        total_value += stock_value
        is_low = bool(
            variant
            and variant.min_stock is not None
            and Decimal(balance.quantity) < Decimal(variant.min_stock)
        )
        if low_stock and not is_low:
            continue
        data.append(
            {
                "variant_id": str(balance.variant_id),
                "product_name": variant.product.name if variant else None,
                "sku": variant.sku if variant else None,
                "unit_name": unit.name if unit else None,
                "quantity": str(balance.quantity),
                "avg_cost": str(balance.avg_cost),
                "stock_value": str(stock_value),
                "min_stock": str(variant.min_stock)
                if variant and variant.min_stock is not None
                else None,
                "low_stock": is_low,
            }
        )
    return {"data": data, "total_value": str(total_value)}


@router.get("/gross-profit")
def gross_profit(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_PROFIT)),
):
    tz = _tz()
    today = datetime.now(tz).date()
    start_day = date.fromisoformat(date_from) if date_from else today
    end_day = date.fromisoformat(date_to) if date_to else today
    start, _ = _day_bounds(start_day)
    _, end = _day_bounds(end_day)

    row = db.execute(
        select(
            func.coalesce(func.sum(Sale.total), 0),
            func.coalesce(func.sum(Sale.cost_total), 0),
            func.count(),
        ).where(Sale.status == "completed", Sale.sold_at >= start, Sale.sold_at < end)
    ).one()
    net_revenue, cost_total, count = row
    return {
        "from_date": start_day.isoformat(),
        "to_date": end_day.isoformat(),
        "net_revenue": str(net_revenue),
        "cost_total": str(cost_total),
        "gross_profit": str(Decimal(net_revenue) - Decimal(cost_total)),
        "sales_count": count,
    }


@router.get("/expenses")
def expenses_report(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_EXPENSE)),
):
    tz = _tz()
    today = datetime.now(tz).date()
    start_day = date.fromisoformat(date_from) if date_from else today
    end_day = date.fromisoformat(date_to) if date_to else today

    rows = (
        db.execute(
            select(Expense).where(
                Expense.cancelled_at.is_(None),
                Expense.expense_date >= start_day,
                Expense.expense_date <= end_day,
            )
        )
        .scalars()
        .all()
    )

    totals: dict = {}
    counts: dict = {}
    grand_total = Decimal(0)
    for expense in rows:
        amount = Decimal(expense.amount)
        grand_total += amount
        totals[expense.category_id] = totals.get(expense.category_id, Decimal(0)) + amount
        counts[expense.category_id] = counts.get(expense.category_id, 0) + 1

    by_category = []
    for category_id, amount in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
        category = db.get(ExpenseCategory, category_id) if category_id else None
        by_category.append(
            {
                "category_id": str(category_id) if category_id else None,
                "category_name": category.name if category else "Tanpa kategori",
                "total": str(amount),
                "count": counts[category_id],
            }
        )

    return {
        "from_date": start_day.isoformat(),
        "to_date": end_day.isoformat(),
        "total": str(grand_total),
        "count": len(rows),
        "by_category": by_category,
    }


@router.get("/sales/payments")
def sales_payments_report(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_SALES)),
):
    tz = _tz()
    today = datetime.now(tz).date()
    start_day = date.fromisoformat(date_from) if date_from else today
    end_day = date.fromisoformat(date_to) if date_to else today
    start, _ = _day_bounds(start_day)
    _, end = _day_bounds(end_day)

    rows = db.execute(
        select(
            Payment.method,
            func.count(),
            func.coalesce(func.sum(Payment.amount), 0),
        )
        .join(Sale, Sale.id == Payment.sale_id)
        .where(Sale.status == "completed", Sale.sold_at >= start, Sale.sold_at < end)
        .group_by(Payment.method)
        .order_by(func.sum(Payment.amount).desc())
    ).all()

    change_total = Decimal(
        db.execute(
            select(func.coalesce(func.sum(Sale.change_total), 0)).where(
                Sale.status == "completed", Sale.sold_at >= start, Sale.sold_at < end
            )
        ).scalar_one()
    )

    data = []
    total = Decimal(0)
    for method, count, amount in rows:
        applied = Decimal(amount) - (change_total if method == "cash" else Decimal(0))
        total += applied
        data.append({"method": method, "count": count, "total": str(applied)})
    return {
        "from_date": start_day.isoformat(),
        "to_date": end_day.isoformat(),
        "total": str(total),
        "data": data,
    }


@router.get("/cashiers")
def cashiers_report(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_SALES)),
):
    tz = _tz()
    today = datetime.now(tz).date()
    start_day = date.fromisoformat(date_from) if date_from else today
    end_day = date.fromisoformat(date_to) if date_to else today
    start, _ = _day_bounds(start_day)
    _, end = _day_bounds(end_day)

    rows = db.execute(
        select(
            Sale.cashier_id,
            func.count(),
            func.coalesce(func.sum(Sale.total), 0),
            func.coalesce(func.sum(Sale.cost_total), 0),
        )
        .where(Sale.status == "completed", Sale.sold_at >= start, Sale.sold_at < end)
        .group_by(Sale.cashier_id)
        .order_by(func.sum(Sale.total).desc())
    ).all()

    data = []
    for cashier_id, count, net, cost in rows:
        cashier = db.get(User, cashier_id)
        data.append(
            {
                "cashier_id": str(cashier_id),
                "cashier_name": cashier.name if cashier else None,
                "sales_count": count,
                "net_revenue": str(net),
                "cost_total": str(cost),
                "gross_profit": str(Decimal(net) - Decimal(cost)),
            }
        )
    return {
        "from_date": start_day.isoformat(),
        "to_date": end_day.isoformat(),
        "data": data,
    }


@router.get("/purchases")
def purchases_report(
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(REPORT_PURCHASE)),
):
    tz = _tz()
    today = datetime.now(tz).date()
    start_day = date.fromisoformat(date_from) if date_from else today
    end_day = date.fromisoformat(date_to) if date_to else today
    start, _ = _day_bounds(start_day)
    _, end = _day_bounds(end_day)

    rows = db.execute(
        select(
            Purchase.supplier_id,
            func.count(),
            func.coalesce(func.sum(Purchase.total), 0),
        )
        .where(
            Purchase.status != "cancelled",
            Purchase.created_at >= start,
            Purchase.created_at < end,
        )
        .group_by(Purchase.supplier_id)
        .order_by(func.sum(Purchase.total).desc())
    ).all()

    data = []
    total = Decimal(0)
    for supplier_id, count, amount in rows:
        supplier = db.get(Supplier, supplier_id) if supplier_id else None
        total += Decimal(amount)
        data.append(
            {
                "supplier_id": str(supplier_id) if supplier_id else None,
                "supplier_name": supplier.name if supplier else "Tanpa supplier",
                "purchases_count": count,
                "total": str(amount),
            }
        )
    return {
        "from_date": start_day.isoformat(),
        "to_date": end_day.isoformat(),
        "total": str(total),
        "data": data,
    }
