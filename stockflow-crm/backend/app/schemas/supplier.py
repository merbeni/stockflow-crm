from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=255)
    contact_name: str = Field(..., max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)


class SupplierResponse(BaseModel):
    id: int
    name: str
    contact_name: str | None
    email: str | None
    phone: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
