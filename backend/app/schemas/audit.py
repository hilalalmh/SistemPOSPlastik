from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class SupplierCreate(BaseModel):
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None


class SupplierOut(ORMModel):
    id: UUID
    name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    is_active: bool


class CustomerCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None


class CustomerOut(ORMModel):
    id: UUID
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    is_active: bool


class AuditLogOut(ORMModel):
    id: UUID
    actor_id: UUID | None = None
    action: str
    entity_type: str
    entity_id: UUID | None = None
    meta: dict | None = None
    created_at: datetime
