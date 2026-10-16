from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.security import hash_password
from app.models.user import Permission, Role, RolePermission, User
from app.permissions import (
    ROLE_READ,
    ROLE_UPDATE,
    USER_CREATE,
    USER_READ,
    USER_UPDATE,
)
from app.schemas.user import (
    PasswordReset,
    PermissionOut,
    RoleOut,
    RolePermissionUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services import audit

router = APIRouter(tags=["users"])


def _to_out(db: Session, user: User) -> dict:
    data = UserOut.model_validate(user).model_dump()
    role = db.get(Role, user.role_id)
    data["role_name"] = role.name if role else None
    return data


@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db), _: User = Depends(require_permission(ROLE_READ))):
    return db.execute(select(Role).order_by(Role.name)).scalars().all()


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(
    db: Session = Depends(get_db), _: User = Depends(require_permission(ROLE_READ))
):
    return db.execute(select(Permission).order_by(Permission.code)).scalars().all()


@router.patch("/roles/{role_id}/permissions", response_model=RoleOut)
def set_role_permissions(
    role_id: UUID,
    payload: RolePermissionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(ROLE_UPDATE)),
):
    role = db.get(Role, role_id)
    if role is None:
        raise NotFoundError("Role tidak ditemukan.")

    targets = (
        db.execute(select(Permission).where(Permission.code.in_(payload.permission_codes)))
        .scalars()
        .all()
    )
    found = {p.code for p in targets}
    missing = set(payload.permission_codes) - found
    if missing:
        raise BusinessRuleError(
            f"Permission tidak dikenal: {', '.join(sorted(missing))}", code="UNKNOWN_PERMISSION"
        )

    db.execute(RolePermission.__table__.delete().where(RolePermission.role_id == role_id))
    for permission in targets:
        db.add(RolePermission(role_id=role_id, permission_id=permission.id))
    audit.log_action(
        db,
        action="role.set_permissions",
        entity_type="role",
        entity_id=role.id,
        actor_id=user.id,
        meta={"permissions": payload.permission_codes},
    )
    db.commit()
    return role


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_permission(USER_READ))):
    users = db.execute(select(User).order_by(User.name)).scalars().all()
    return {"data": [_to_out(db, u) for u in users]}


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(USER_CREATE)),
):
    exists = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if exists is not None:
        raise BusinessRuleError("Username sudah digunakan.", code="USERNAME_EXISTS")
    if db.get(Role, payload.role_id) is None:
        raise NotFoundError("Role tidak ditemukan.")
    user = User(
        name=payload.name,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=payload.role_id,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()
    audit.log_action(
        db, action="user.create", entity_type="user", entity_id=user.id, actor_id=actor.id
    )
    db.commit()
    db.refresh(user)
    return _to_out(db, user)


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(USER_READ)),
):
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Pengguna tidak ditemukan.")
    return _to_out(db, user)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(USER_UPDATE)),
):
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Pengguna tidak ditemukan.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    audit.log_action(
        db,
        action="user.update",
        entity_type="user",
        entity_id=user.id,
        actor_id=actor.id,
        meta=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(user)
    return _to_out(db, user)


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(USER_UPDATE)),
):
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Pengguna tidak ditemukan.")
    if user.id == actor.id:
        raise BusinessRuleError("Tidak dapat menonaktifkan akun sendiri.", code="SELF_DEACTIVATE")
    user.is_active = False
    audit.log_action(
        db, action="user.deactivate", entity_type="user", entity_id=user.id, actor_id=actor.id
    )
    db.commit()
    db.refresh(user)
    return _to_out(db, user)


@router.post("/users/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: UUID,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(USER_UPDATE)),
):
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Pengguna tidak ditemukan.")
    user.password_hash = hash_password(payload.new_password)
    audit.log_action(
        db, action="user.reset_password", entity_type="user", entity_id=user.id, actor_id=actor.id
    )
    db.commit()
    db.refresh(user)
    return _to_out(db, user)
