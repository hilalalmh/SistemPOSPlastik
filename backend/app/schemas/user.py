from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class RoleOut(ORMModel):
    id: UUID
    name: str
    description: str | None = None


class PermissionOut(ORMModel):
    id: UUID
    code: str
    description: str | None = None


class UserOut(ORMModel):
    id: UUID
    name: str
    username: str
    email: str | None = None
    role_id: UUID
    is_active: bool
    role_name: str | None = None


class UserCreate(BaseModel):
    name: str
    username: str
    email: str | None = None
    password: str
    role_id: UUID
    is_active: bool = True


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    role_id: UUID | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    new_password: str


class RolePermissionUpdate(BaseModel):
    permission_codes: list[str]
