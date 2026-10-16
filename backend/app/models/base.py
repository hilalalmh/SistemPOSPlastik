import uuid
from datetime import UTC, datetime

from sqlalchemy import Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.dbtypes import UTCDateTime


def utcnow() -> datetime:
    return datetime.now(UTC)


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )


# Reusable column types matching the ERD precision policy.
def money_column(**kwargs):
    return mapped_column(Numeric(18, 2), **kwargs)


def quantity_column(**kwargs):
    return mapped_column(Numeric(18, 4), **kwargs)
