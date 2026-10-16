from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Store timestamps in UTC and always return timezone-aware UTC datetimes.

    Databases such as MySQL have no timezone-aware timestamp type, so naive
    values are persisted as UTC and re-attached with UTC on the way out. This
    keeps application code (comparisons, ``astimezone``) consistent regardless
    of the underlying database engine.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        value = value.astimezone(UTC)
        if dialect.name in ("mysql", "mariadb"):
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
