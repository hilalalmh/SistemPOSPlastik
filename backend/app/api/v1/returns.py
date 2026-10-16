from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.pagination import Pagination, pagination_params
from app.core.database import get_db
from app.models.return_ import Return
from app.models.user import User
from app.permissions import RETURN_CONFIRM, RETURN_CREATE, RETURN_READ
from app.schemas.common import Page
from app.schemas.return_ import ReturnCreate, ReturnOut
from app.services import audit
from app.services import returns as returns_service

router = APIRouter(prefix="/returns", tags=["returns"])


@router.get("", response_model=Page[ReturnOut])
def list_returns(
    status: str | None = None,
    type: str | None = None,
    sale_id: UUID | None = None,
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(RETURN_READ)),
):
    stmt = returns_service.return_query()
    count_stmt = select(func.count()).select_from(Return)
    if status:
        stmt = stmt.where(Return.status == status)
        count_stmt = count_stmt.where(Return.status == status)
    if type:
        stmt = stmt.where(Return.type == type)
        count_stmt = count_stmt.where(Return.type == type)
    if sale_id:
        stmt = stmt.where(Return.sale_id == sale_id)
        count_stmt = count_stmt.where(Return.sale_id == sale_id)

    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(Return.created_at.desc()).offset(page.offset).limit(page.page_size)
        )
        .scalars()
        .all()
    )
    return {
        "data": [returns_service.serialize_return(db, row) for row in rows],
        "page": page.page,
        "page_size": page.page_size,
        "total": total,
    }


@router.post("", response_model=ReturnOut, status_code=201)
def create_return(
    payload: ReturnCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(RETURN_CREATE)),
):
    ret = returns_service.create_return(db, payload, created_by=user.id)
    audit.log_action(
        db,
        action="return.create",
        entity_type="return",
        entity_id=ret.id,
        actor_id=user.id,
        meta={"number": ret.number, "refund_amount": str(ret.refund_amount)},
    )
    db.commit()
    db.refresh(ret)
    return returns_service.serialize_return(db, ret)


@router.get("/{return_id}", response_model=ReturnOut)
def get_return(
    return_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(RETURN_READ)),
):
    return returns_service.serialize_return(db, returns_service.get_return(db, return_id))


@router.post("/{return_id}/confirm", response_model=ReturnOut)
def confirm_return(
    return_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(RETURN_CONFIRM)),
):
    ret = returns_service.get_return(db, return_id)
    returns_service.confirm_return(db, ret, approved_by=user.id)
    audit.log_action(
        db,
        action="return.confirm",
        entity_type="return",
        entity_id=ret.id,
        actor_id=user.id,
        meta={"number": ret.number, "refund_amount": str(ret.refund_amount)},
    )
    db.commit()
    db.refresh(ret)
    return returns_service.serialize_return(db, ret)


@router.post("/{return_id}/cancel", response_model=ReturnOut)
def cancel_return(
    return_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(RETURN_CREATE, RETURN_CONFIRM, mode="any")),
):
    ret = returns_service.get_return(db, return_id)
    returns_service.cancel_return(db, ret)
    audit.log_action(
        db,
        action="return.cancel",
        entity_type="return",
        entity_id=ret.id,
        actor_id=user.id,
        meta={"number": ret.number},
    )
    db.commit()
    db.refresh(ret)
    return returns_service.serialize_return(db, ret)
