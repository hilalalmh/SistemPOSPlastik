from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UUIDMixin


class StoreSetting(UUIDMixin, Base):
    __tablename__ = "store_settings"

    store_name: Mapped[str] = mapped_column(String(150), nullable=False, default="Toko Plastik")
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    logo_url: Mapped[str | None] = mapped_column(Text)
    receipt_header: Mapped[str | None] = mapped_column(Text)
    receipt_footer: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Jakarta")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    invoice_prefix_sale: Mapped[str] = mapped_column(String(10), nullable=False, default="SLS")
    invoice_prefix_purchase: Mapped[str] = mapped_column(String(10), nullable=False, default="PUR")
    invoice_prefix_return: Mapped[str] = mapped_column(String(10), nullable=False, default="RTR")
    discount_max_percent_cashier: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )
    allow_negative_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Location(UUIDMixin, Base):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DocumentCounter(Base):
    __tablename__ = "document_counters"

    prefix: Mapped[str] = mapped_column(String(10), primary_key=True)
    period: Mapped[str] = mapped_column(String(6), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
