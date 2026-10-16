import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.dbtypes import UTCDateTime
from app.models.base import UUIDMixin


class ExpenseCategory(UUIDMixin, Base):
    __tablename__ = "expense_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Expense(UUIDMixin, Base):
    __tablename__ = "expenses"

    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("expense_categories.id"))
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    attachment_url: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
