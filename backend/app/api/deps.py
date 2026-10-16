from collections.abc import Callable
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthError
from app.core.exceptions import PermissionError_ as ForbiddenError
from app.models.user import Permission, RolePermission, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthError("Autentikasi diperlukan.")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[settings.algorithm]
        )
    except jwt.PyJWTError as exc:
        raise AuthError("Token tidak valid atau sudah kedaluwarsa.") from exc

    if payload.get("type") != "access":
        raise AuthError("Tipe token tidak valid.")

    user = db.get(User, UUID(payload.get("sub")))
    if user is None or not user.is_active:
        raise AuthError("Pengguna tidak ditemukan atau tidak aktif.")
    return user


def get_user_permissions(db: Session, user: User) -> set[str]:
    rows = db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == user.role_id)
    ).scalars()
    return set(rows)


def require_permission(*codes: str, mode: str = "all") -> Callable:
    """Dependency factory enforcing backend permission checks (production.md Bagian 3)."""

    def dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        granted = get_user_permissions(db, user)
        if mode == "any":
            ok = any(code in granted for code in codes)
        else:
            ok = all(code in granted for code in codes)
        if not ok:
            raise ForbiddenError("Anda tidak memiliki izin untuk tindakan ini.")
        return user

    return dependency


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
