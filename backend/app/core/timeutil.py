from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings

DEFAULT_TIMEZONE = "Asia/Jakarta"


def tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.timezone)
    except Exception:  # noqa: BLE001
        return ZoneInfo(DEFAULT_TIMEZONE)


def day_bounds(target: date) -> tuple[datetime, datetime]:
    """Return the [start, end) instants covering an entire local day."""
    start = datetime.combine(target, time.min, tzinfo=tz())
    return start, start + timedelta(days=1)
