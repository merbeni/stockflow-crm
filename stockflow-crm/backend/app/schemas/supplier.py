from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.validators import (
    NombrePersona,
    NombrePersonaOpcional,
    TelefonoOpcional,
    TextoObligatorio,
)


class SupplierCreate(BaseModel):
    # El nombre del proveedor es el de una empresa: admite números.
    name: TextoObligatorio(255)
    contact_name: NombrePersona()
    email: EmailStr
    phone: TelefonoOpcional = None


class SupplierUpdate(BaseModel):
    name: TextoObligatorio(255) | None = None
    contact_name: NombrePersonaOpcional() = None
    email: EmailStr | None = None
    phone: TelefonoOpcional = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    contact_name: str | None
    email: str | None
    phone: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
