from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.models.invoice import ConfidenceLevel, InvoiceStatus


# ── Gemini / process response ─────────────────────────────────────────────────

class InvoiceItemProcessed(BaseModel):
    """One item returned by Gemini, enriched with auto-match suggestions."""
    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    confidence: ConfidenceLevel
    suggested_product_id: int | None = None
    suggested_product_name: str | None = None
    suggested_supplier_sku: str | None = None

    model_config = {"from_attributes": True}


class InvoiceProcessResponse(BaseModel):
    """Returned immediately after uploading an invoice for processing."""
    invoice_id: int
    supplier: str | None
    supplier_id: int | None
    date: date | None
    items: list[InvoiceItemProcessed]
    # Maps product_id → supplier_sku for every known mapping of the detected supplier.
    # Used by the frontend to auto-fill the Supplier SKU field on product selection.
    supplier_product_skus: dict[int, str] = {}


# ── Confirm request ───────────────────────────────────────────────────────────

class NewSupplierData(BaseModel):
    name: str = Field(..., max_length=255)
    contact_name: str = Field(..., max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)


class NewProductData(BaseModel):
    sku: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: str | None = None
    price: Decimal = Field(..., ge=0, decimal_places=2)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=3)


class InvoiceConfirmItem(BaseModel):
    invoice_item_id: int
    # Provide exactly one of product_id or new_product (or skip=True).
    product_id: int | None = None
    new_product: NewProductData | None = None
    # If set, saves a ProductSupplierMapping so future invoices auto-match.
    supplier_sku: str | None = None
    skip: bool = False


class InvoiceConfirmPayload(BaseModel):
    items: list[InvoiceConfirmItem]
    # Supplier resolution: provide supplier_id to link existing, or new_supplier to create.
    supplier_id: int | None = None
    new_supplier: NewSupplierData | None = None


# ── General list / detail responses ──────────────────────────────────────────

class InvoiceItemResponse(BaseModel):
    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    confidence: ConfidenceLevel
    supplier_sku: str | None
    skipped: bool = False

    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    id: int
    supplier_id: int | None
    supplier_name: str | None = None
    date: date | None
    file_url: str | None
    status: InvoiceStatus
    created_at: datetime
    items: list[InvoiceItemResponse]

    model_config = {"from_attributes": True}
