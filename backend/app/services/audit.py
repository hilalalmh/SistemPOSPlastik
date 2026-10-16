from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import AuditLog


def log_action(
    db: Session,
    *,
    action: str,
    entity_type: str,
    actor_id: UUID | None = None,
    entity_id: UUID | None = None,
    meta: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Append an audit entry. Never store secrets, passwords, or tokens here."""
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        meta=meta or {},
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
