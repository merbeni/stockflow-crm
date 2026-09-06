from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.order import OrderStatus
from app.schemas.validators import (
    CorreoElectronico,
    CorreoOpcional,
    NombrePersona,
    Telefono,
    TelefonoOpcional,
    TextoOpcional,
)


# ── Customer CRUD ─────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: NombrePersona()
    email: CorreoElectronico
    phone: Telefono
    address: TextoOpcional(500) = None


class CustomerUpdate(BaseModel):
    name: NombrePersona() | None = None
    email: CorreoOpcional = None
    phone: TelefonoOpcional = None
    address: TextoOpcional(500) = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str | None
    phone: str | None
    address: str | None
    created_at: datetime
    # Lo calcula el servicio: permite deshabilitar el botón de borrado con su
    # explicación, en vez de que la acción falle al pulsarla.
    can_delete: bool = False
    delete_blocked_reason: str | None = None

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
