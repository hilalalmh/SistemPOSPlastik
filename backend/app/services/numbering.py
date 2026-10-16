from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.store import DocumentCounter


def generate_number(db: Session, prefix: str, when: datetime | None = None) -> str:
    """Generate a document number as {PREFIX}-{YYYYMM}-{URUT6}.

    Must be called inside an active transaction. Uses row-level locking to keep
    the sequence unique per prefix/period (production.md Bagian 5 butir 15).
    """
    moment = when or datetime.now(UTC)
    period = moment.strftime("%Y%m")

    counter = db.execute(
        select(DocumentCounter)
        .where(DocumentCounter.prefix == prefix, DocumentCounter.period == period)
        .with_for_update()
    ).scalar_one_or_none()

    if counter is None:
        counter = DocumentCounter(prefix=prefix, period=period, last_number=0)
        db.add(counter)
        db.flush()

    counter.last_number += 1
    db.flush()
    return f"{prefix}-{period}-{counter.last_number:06d}"
