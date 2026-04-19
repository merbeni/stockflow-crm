from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.invoice import ConfidenceLevel, InvoiceStatus
from app.models.order import OrderStatus
from app.models.stock_movement import MovementType


# ── Embedded summaries ────────────────────────────────────────────────────────

class ProductSummary(BaseModel):
    id: int
    sku: str
    name: str

    model_config = {"from_attributes": True}


class InvoiceItemSummary(BaseModel):
    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    confidence: ConfidenceLevel
    supplier_sku: str | None

    model_config = {"from_attributes": True}


class InvoiceSummary(BaseModel):
    id: int
    date: date | None
    status: InvoiceStatus
    supplier_name: str | None = None

    model_config = {"from_attributes": True}


class InvoiceDetail(InvoiceSummary):
    """Extended invoice info — only included in movement detail response."""
    gemini_raw: dict | None = None
    items: list[InvoiceItemSummary] = []


class OrderSummary(BaseModel):
    id: int
    status: OrderStatus
    customer_name: str | None = None

    model_config = {"from_attributes": True}


# ── Movement responses ────────────────────────────────────────────────────────

class StockMovementResponse(BaseModel):
    """Lightweight response used in the list endpoint."""
    id: int
    created_at: datetime
    product: ProductSummary
    quantity: Decimal
    type: MovementType
    invoice_id: int | None
    order_id: int | None
    # Thin origin summary (no gemini_raw / items)
    invoice: InvoiceSummary | None = None
    order: OrderSummary | None = None

    model_config = {"from_attributes": True}


class StockMovementDetail(BaseModel):
    """Full response used in the detail endpoint (includes gemini_raw + items)."""
    id: int
    created_at: datetime
    product: ProductSummary
    quantity: Decimal
    type: MovementType
    invoice_id: int | None
    order_id: int | None
    invoice: InvoiceDetail | None = None
    order: OrderSummary | None = None

    model_config = {"from_attributes": True}
