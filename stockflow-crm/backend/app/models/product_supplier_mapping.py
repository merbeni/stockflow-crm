from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.supplier import Supplier


class ProductSupplierMapping(Base):
    __tablename__ = "product_supplier_mappings"
    __table_args__ = (
        UniqueConstraint("supplier_id", "supplier_sku", name="uq_supplier_sku"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    supplier_sku: Mapped[str] = mapped_column(String(100), nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="supplier_mappings")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="product_mappings")
