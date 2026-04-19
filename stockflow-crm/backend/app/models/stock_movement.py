import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.order import Order
    from app.models.product import Product


class MovementType(str, enum.Enum):
    entry = "entry"
    exit = "exit"
    adjustment = "adjustment"


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, name="movementtype"), nullable=False
    )
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship("Product", back_populates="stock_movements")
    invoice: Mapped["Invoice | None"] = relationship("Invoice", back_populates="stock_movements")
    order: Mapped["Order | None"] = relationship("Order", back_populates="stock_movements")
