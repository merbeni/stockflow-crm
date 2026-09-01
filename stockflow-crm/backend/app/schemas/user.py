from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole
from app.schemas.validators import (
    NombrePersona,
    Password,
    Telefono,
    TelefonoOpcional,
    TextoObligatorio,
)


# ── Alta pública (crea organización + administrador) ──────────────────────────

class SignupRequest(BaseModel):
    """Registro público: da de alta una organización nueva y su administrador."""

    organization_name: TextoObligatorio(255)
    full_name: NombrePersona()
    email: EmailStr
    phone: Telefono
    password: Password


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Alta interna (la realiza un administrador dentro de su organización) ──────

class UserCreate(BaseModel):
    email: EmailStr
    password: Password
    full_name: NombrePersona()
    phone: TelefonoOpcional = None
    role: UserRole = UserRole.operator


class UserUpdate(BaseModel):
    """Cambios que un administrador puede aplicar sobre otro usuario."""

    role: UserRole | None = None
    is_active: bool | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


# ── Respuestas ────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    phone: str | None = None
    role: UserRole
    organization_id: int
    is_active: bool
    is_email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SignupResponse(BaseModel):
    """Confirmación explícita del alta, para que el usuario sepa qué sigue."""

    message: str
    user: UserResponse
    organization: OrganizationResponse
    email_verification_required: bool = True


class MessageResponse(BaseModel):
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
