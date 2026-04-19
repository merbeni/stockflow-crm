from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


# ── Requests ──────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    customer_id: int


class OrderItemAdd(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0, decimal_places=3)
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)


# ── Responses ─────────────────────────────────────────────────────────────────

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_sku: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    customer_email: str | None = None
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemResponse]
    total: Decimal
