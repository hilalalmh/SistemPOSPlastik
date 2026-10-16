import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.dbtypes import UTCDateTime
from app.models.base import TimestampMixin, UUIDMixin


class Role(UUIDMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(back_populates="role")


class Permission(UUIDMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship(back_populates="role_permissions")


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    role: Mapped[Role] = relationship(back_populates="users")


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column()
    meta: Mapped[dict | None] = mapped_column("metadata", JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )


class IdempotencyKey(UUIDMixin, Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("key", name="uq_idempotency_key"),)

    key: Mapped[str] = mapped_column(String(150), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(150), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
