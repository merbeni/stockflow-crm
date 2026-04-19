# Import all models here so Alembic can discover them via Base.metadata.
from app.models.customer import Customer
from app.models.invoice import ConfidenceLevel, Invoice, InvoiceItem, InvoiceStatus
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.product_supplier_mapping import ProductSupplierMapping
from app.models.stock_movement import MovementType, StockMovement
from app.models.supplier import Supplier
from app.models.user import User, UserRole

__all__ = [
    "User",
    "UserRole",
    "Customer",
    "Supplier",
    "Product",
    "Invoice",
    "InvoiceItem",
    "InvoiceStatus",
    "ConfidenceLevel",
    "StockMovement",
    "MovementType",
    "Order",
    "OrderItem",
    "OrderStatus",
    "ProductSupplierMapping",
]
