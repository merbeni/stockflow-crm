from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr

from app.models.order import OrderStatus
from app.schemas.validators import NombrePersona, Telefono, TelefonoOpcional, TextoOpcional


# ── Customer CRUD ─────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: NombrePersona()
    email: EmailStr
    phone: Telefono
    address: TextoOpcional(500) = None


class CustomerUpdate(BaseModel):
    name: NombrePersona() | None = None
    email: EmailStr | None = None
    phone: TelefonoOpcional = None
    address: TextoOpcional(500) = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str | None
    phone: str | None
    address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Order history ─────────────────────────────────────────────────────────────

class OrderItemSummary(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal

    model_config = {"from_attributes": True}


class OrderHistoryEntry(BaseModel):
    id: int
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemSummary]
    total: Decimal

    model_config = {"from_attributes": True}


class CustomerOrderHistory(BaseModel):
    customer: CustomerResponse
    orders: list[OrderHistoryEntry]
