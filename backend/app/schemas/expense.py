from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import MoneyStr, ORMModel


class ExpenseCategoryCreate(BaseModel):
    name: str
    is_active: bool = True


class ExpenseCategoryOut(ORMModel):
    id: UUID
    name: str
    is_active: bool


class ExpenseCreate(BaseModel):
    category_id: UUID | None = None
    expense_date: date
    amount: Decimal
    payment_method: str
    description: str | None = None
    attachment_url: str | None = None


class ExpenseOut(ORMModel):
    id: UUID
    category_id: UUID | None = None
    category_name: str | None = None
    expense_date: date
    amount: MoneyStr
    payment_method: str
    description: str | None = None
    attachment_url: str | None = None
    user_id: UUID
    cancelled_at: datetime | None = None
    cancelled_by: UUID | None = None
    created_at: datetime
