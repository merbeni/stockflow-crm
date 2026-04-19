from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order
from app.models.stock_movement import MovementType, StockMovement
from app.models.supplier import Supplier


def list_movements(
    db: Session,
    *,
    product_id: int | None = None,
    movement_type: MovementType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[StockMovement]:
    stmt = (
        select(StockMovement)
        .options(
            joinedload(StockMovement.product),
            joinedload(StockMovement.invoice).joinedload(Invoice.supplier),
            joinedload(StockMovement.order).joinedload(Order.customer),
        )
        .order_by(StockMovement.created_at.desc())
    )

    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if movement_type is not None:
        stmt = stmt.where(StockMovement.type == movement_type)
    if date_from is not None:
        stmt = stmt.where(StockMovement.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(StockMovement.created_at <= date_to)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).unique())


def get_movement(db: Session, movement_id: int) -> StockMovement | None:
    stmt = (
        select(StockMovement)
        .where(StockMovement.id == movement_id)
        .options(
            joinedload(StockMovement.product),
            joinedload(StockMovement.invoice).joinedload(Invoice.supplier),
            joinedload(StockMovement.invoice).joinedload(Invoice.items),
            joinedload(StockMovement.order).joinedload(Order.customer),
        )
    )
    return db.scalars(stmt).first()
