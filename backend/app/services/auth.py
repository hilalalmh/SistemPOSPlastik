from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthError
from app.core.security import verify_password
from app.models.base import utcnow
from app.models.user import User
from app.services import audit


def authenticate(db: Session, username: str, password: str, ip: str | None = None) -> User:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()

    if user is None:
        audit.log_action(
            db,
            action="auth.login_failed",
            entity_type="user",
            meta={"username": username, "reason": "not_found"},
            ip_address=ip,
        )
        db.commit()
        raise AuthError("Username atau password salah.")

    if user.locked_until is not None and user.locked_until > utcnow():
        raise AuthError("Akun terkunci sementara. Coba lagi nanti.", code="ACCOUNT_LOCKED")

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.login_max_attempts:
            user.locked_until = utcnow() + timedelta(minutes=settings.login_lock_minutes)
        audit.log_action(
            db,
            action="auth.login_failed",
            entity_type="user",
            actor_id=user.id,
            entity_id=user.id,
            meta={"reason": "bad_password"},
            ip_address=ip,
        )
        db.commit()
        raise AuthError("Username atau password salah.")

    if not user.is_active:
        raise AuthError("Akun tidak aktif.", code="ACCOUNT_INACTIVE")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    audit.log_action(
        db,
        action="auth.login",
        entity_type="user",
        actor_id=user.id,
        entity_id=user.id,
        ip_address=ip,
    )
    db.commit()
    return user
