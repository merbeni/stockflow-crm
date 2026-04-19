from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.order import OrderItem
    from app.models.product_supplier_mapping import ProductSupplierMapping
    from app.models.stock_movement import StockMovement


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    current_stock: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False, default=0.0)
    minimum_stock: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement", back_populates="product", passive_deletes=True
    )
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="product")
    supplier_mappings: Mapped[list["ProductSupplierMapping"]] = relationship(
        "ProductSupplierMapping", back_populates="product"
    )
