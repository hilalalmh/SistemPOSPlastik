from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.expense import Expense, ExpenseCategory


def q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def list_categories(db: Session, *, active_only: bool = False) -> list[ExpenseCategory]:
    stmt = select(ExpenseCategory).order_by(ExpenseCategory.name)
    if active_only:
        stmt = stmt.where(ExpenseCategory.is_active.is_(True))
    return db.execute(stmt).scalars().all()


def create_category(db: Session, name: str, *, is_active: bool = True) -> ExpenseCategory:
    cleaned = (name or "").strip()
    if not cleaned:
        raise BusinessRuleError("Nama kategori wajib diisi.", code="NAME_REQUIRED")
    existing = db.execute(
        select(ExpenseCategory).where(ExpenseCategory.name == cleaned)
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Kategori sudah ada.", code="CATEGORY_EXISTS")
    category = ExpenseCategory(name=cleaned, is_active=is_active)
    db.add(category)
    db.flush()
    return category


def get_expense(db: Session, expense_id: UUID) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise NotFoundError("Pengeluaran tidak ditemukan.", code="EXPENSE_NOT_FOUND")
    return expense


def create_expense(db: Session, payload, *, user_id: UUID) -> Expense:
    amount = q2(payload.amount)
    if amount <= 0:
        raise BusinessRuleError("Nominal harus lebih dari nol.", code="INVALID_AMOUNT")
    method = (payload.payment_method or "").strip()
    if not method:
        raise BusinessRuleError("Metode pembayaran wajib diisi.", code="METHOD_REQUIRED")
    if payload.category_id is not None and db.get(ExpenseCategory, payload.category_id) is None:
        raise BusinessRuleError("Kategori tidak ditemukan.", code="CATEGORY_NOT_FOUND")

    expense = Expense(
        category_id=payload.category_id,
        expense_date=payload.expense_date,
        amount=amount,
        payment_method=method,
        description=payload.description,
        attachment_url=payload.attachment_url,
        user_id=user_id,
    )
    db.add(expense)
    db.flush()
    return expense


def cancel_expense(db: Session, expense: Expense, *, cancelled_by: UUID) -> Expense:
    if expense.cancelled_at is not None:
        raise ConflictError("Pengeluaran sudah dibatalkan.", code="EXPENSE_ALREADY_CANCELLED")
    expense.cancelled_at = datetime.now(UTC)
    expense.cancelled_by = cancelled_by
    db.flush()
    return expense


def serialize_expense(db: Session, expense: Expense) -> dict:
    category = db.get(ExpenseCategory, expense.category_id) if expense.category_id else None
    return {
        "id": expense.id,
        "category_id": expense.category_id,
        "category_name": category.name if category else None,
        "expense_date": expense.expense_date,
        "amount": expense.amount,
        "payment_method": expense.payment_method,
        "description": expense.description,
        "attachment_url": expense.attachment_url,
        "user_id": expense.user_id,
        "cancelled_at": expense.cancelled_at,
        "cancelled_by": expense.cancelled_by,
        "created_at": expense.created_at,
    }
