from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Role
    department_id: int | None = None


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    role: Role | None = None
    department_id: int | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: Role
    department_id: int | None = None
    created_at: datetime
