from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.order import OrderItem
    from app.models.product_supplier_mapping import ProductSupplierMapping
    from app.models.stock_movement import StockMovement


class Product(Base):
    __tablename__ = "products"
    # El SKU es único dentro de cada organización, no a nivel global: dos
    # empresas distintas pueden usar legítimamente el mismo código.
    __table_args__ = (
        UniqueConstraint("organization_id", "sku", name="uq_product_org_sku"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    current_stock: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False, default=0.0)
    minimum_stock: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False, default=0.0)
    # Los productos unitarios (por defecto) no admiten cantidades fraccionarias:
    # "3.5 teclados" es un error de integridad. Se habilita para artículos a
    # granel medidos en kg, litros o metros.
    allow_decimal_stock: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Sin passive_deletes: los movimientos internos del producto se borran en la
    # misma transacción. Antes se delegaba a la base, que los rechazaba por el
    # ondelete="RESTRICT" de la clave foránea y hacía indeleteable al producto.
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement", back_populates="product"
    )
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="product")
    supplier_mappings: Mapped[list["ProductSupplierMapping"]] = relationship(
        "ProductSupplierMapping", back_populates="product", cascade="all, delete-orphan"
    )
