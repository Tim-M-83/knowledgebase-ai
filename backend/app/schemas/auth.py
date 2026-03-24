from pydantic import BaseModel, EmailStr

from app.models.user import Role


class LoginRequest(BaseModel):
    email: str
    password: str


class CredentialUpdateRequest(BaseModel):
    current_password: str | None = None
    new_email: EmailStr | None = None
    new_password: str | None = None


class CredentialUpdateResponse(BaseModel):
    message: str


class MeResponse(BaseModel):
    id: int
    email: str
    role: Role
    department_id: int | None = None
    email_helper_enabled: bool = True
    license_enabled: bool = False
    license_active: bool = False
    license_status: str | None = None
    license_grace_until: str | None = None
    must_change_credentials: bool = False
