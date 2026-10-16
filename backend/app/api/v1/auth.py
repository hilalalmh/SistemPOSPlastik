from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_user, get_user_permissions
from app.core.database import get_db
from app.core.exceptions import AuthError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshTokenRequest
from app.services import audit
from app.services.auth import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_payload(db: Session, user: User) -> dict:
    return {
        "id": str(user.id),
        "name": user.name,
        "role": user.role.name,
        "permissions": sorted(get_user_permissions(db, user)),
    }


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = authenticate(db, payload.username, payload.password, ip=client_ip(request))
    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
        "expires_in": 3600,
        "user": _user_payload(db, user),
    }


@router.post("/refresh")
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)):

    try:
        data = decode_token(payload.refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise AuthError("Refresh token tidak valid.") from exc
    if data.get("type") != "refresh":
        raise AuthError("Tipe token tidak valid.")
    user = db.get(User, UUID(data["sub"]))
    if user is None or not user.is_active:
        raise AuthError("Pengguna tidak ditemukan atau tidak aktif.")
    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
        "expires_in": 3600,
        "user": _user_payload(db, user),
    }


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit.log_action(
        db, action="auth.logout", entity_type="user", actor_id=user.id, entity_id=user.id
    )
    db.commit()
    return {"message": "Berhasil keluar."}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_payload(db, user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise AuthError("Password lama salah.")
    user.password_hash = hash_password(payload.new_password)
    audit.log_action(
        db, action="auth.change_password", entity_type="user", actor_id=user.id, entity_id=user.id
    )
    db.commit()
    return {"message": "Password berhasil diubah."}
