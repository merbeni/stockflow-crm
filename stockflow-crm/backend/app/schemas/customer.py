from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.models.order import OrderStatus


# ── Customer CRUD ─────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    phone: str = Field(..., max_length=50)
    address: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None


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
