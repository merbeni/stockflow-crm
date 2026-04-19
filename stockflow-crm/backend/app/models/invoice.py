import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.stock_movement import StockMovement
    from app.models.supplier import Supplier


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class ConfidenceLevel(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gemini_raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoicestatus"),
        nullable=False,
        default=InvoiceStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    supplier: Mapped["Supplier | None"] = relationship("Supplier", back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(
        "InvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement", back_populates="invoice"
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    confidence: Mapped[ConfidenceLevel] = mapped_column(
        Enum(ConfidenceLevel, name="confidencelevel"), nullable=False
    )
    supplier_sku: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items")
