from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.models.user import AuditLog, User
from app.permissions import AUDIT_READ

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
def list_audit_logs(
    actor_id: UUID | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(AUDIT_READ)),
):
    stmt = select(AuditLog)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(AuditLog.created_at.desc()).offset(page.offset).limit(page.page_size)
        )
        .scalars()
        .all()
    )
    return {
        "data": [
            {
                "id": str(r.id),
                "actor_id": str(r.actor_id) if r.actor_id else None,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "meta": r.meta,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }
