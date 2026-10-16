from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.models.expense import Expense
from app.models.user import User
from app.permissions import EXPENSE_READ, EXPENSE_UPDATE
from app.schemas.common import Page
from app.schemas.expense import (
    ExpenseCategoryCreate,
    ExpenseCategoryOut,
    ExpenseCreate,
    ExpenseOut,
)
from app.services import audit
from app.services import expenses as expenses_service

router = APIRouter(tags=["expenses"])


@router.get("/expense-categories")
def list_expense_categories(
    active_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(EXPENSE_READ)),
):
    rows = expenses_service.list_categories(db, active_only=active_only)
    return {"data": [ExpenseCategoryOut.model_validate(c) for c in rows]}


@router.post("/expense-categories", response_model=ExpenseCategoryOut, status_code=201)
def create_expense_category(
    payload: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EXPENSE_UPDATE)),
):
    category = expenses_service.create_category(db, payload.name, is_active=payload.is_active)
    audit.log_action(
        db,
        action="expense_category.create",
        entity_type="expense_category",
        entity_id=category.id,
        actor_id=user.id,
        meta={"name": category.name},
    )
    db.commit()
    db.refresh(category)
    return category


@router.get("/expenses", response_model=Page[ExpenseOut])
def list_expenses(
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: UUID | None = None,
    include_cancelled: bool = False,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(EXPENSE_READ)),
):
    stmt = select(Expense)
    count_stmt = select(func.count()).select_from(Expense)
    if date_from is not None:
        stmt = stmt.where(Expense.expense_date >= date_from)
        count_stmt = count_stmt.where(Expense.expense_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Expense.expense_date <= date_to)
        count_stmt = count_stmt.where(Expense.expense_date <= date_to)
    if category_id is not None:
        stmt = stmt.where(Expense.category_id == category_id)
        count_stmt = count_stmt.where(Expense.category_id == category_id)
    if not include_cancelled:
        stmt = stmt.where(Expense.cancelled_at.is_(None))
        count_stmt = count_stmt.where(Expense.cancelled_at.is_(None))

    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(Expense.expense_date.desc(), Expense.created_at.desc())
            .offset(page.offset)
            .limit(page.page_size)
        )
        .scalars()
        .all()
    )
    return {
        "data": [expenses_service.serialize_expense(db, row) for row in rows],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EXPENSE_UPDATE)),
):
    expense = expenses_service.create_expense(db, payload, user_id=user.id)
    audit.log_action(
        db,
        action="expense.create",
        entity_type="expense",
        entity_id=expense.id,
        actor_id=user.id,
        meta={"amount": str(expense.amount), "method": expense.payment_method},
    )
    db.commit()
    db.refresh(expense)
    return expenses_service.serialize_expense(db, expense)


@router.post("/expenses/{expense_id}/cancel", response_model=ExpenseOut)
def cancel_expense(
    expense_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EXPENSE_UPDATE)),
):
    expense = expenses_service.get_expense(db, expense_id)
    expenses_service.cancel_expense(db, expense, cancelled_by=user.id)
    audit.log_action(
        db,
        action="expense.cancel",
        entity_type="expense",
        entity_id=expense.id,
        actor_id=user.id,
    )
    db.commit()
    db.refresh(expense)
    return expenses_service.serialize_expense(db, expense)
