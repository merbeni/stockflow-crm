from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.stock_movement import MovementType
from app.schemas.stock_movement import (
    InvoiceDetail,
    InvoiceSummary,
    OrderSummary,
    ProductSummary,
    StockMovementDetail,
    StockMovementResponse,
)
from app.services.stock_movement_service import get_movement, list_movements

router = APIRouter(
    prefix="/stock-movements",
    tags=["stock-movements"],
    dependencies=[Depends(get_current_user)],
)


def _build_list_response(movement) -> StockMovementResponse:
    invoice_summary = None
    if movement.invoice:
        inv = movement.invoice
        invoice_summary = InvoiceSummary(
            id=inv.id,
            date=inv.date,
            status=inv.status,
            supplier_name=inv.supplier.name if inv.supplier else None,
        )

    order_summary = None
    if movement.order:
        ord_ = movement.order
        order_summary = OrderSummary(
            id=ord_.id,
            status=ord_.status,
            customer_name=ord_.customer.name if ord_.customer else None,
        )

    return StockMovementResponse(
        id=movement.id,
        created_at=movement.created_at,
        product=ProductSummary.model_validate(movement.product),
        quantity=movement.quantity,
        type=movement.type,
        invoice_id=movement.invoice_id,
        order_id=movement.order_id,
        invoice=invoice_summary,
        order=order_summary,
    )


def _build_detail_response(movement) -> StockMovementDetail:
    invoice_detail = None
    if movement.invoice:
        inv = movement.invoice
        invoice_detail = InvoiceDetail(
            id=inv.id,
            date=inv.date,
            status=inv.status,
            supplier_name=inv.supplier.name if inv.supplier else None,
            gemini_raw=inv.gemini_raw,
            items=inv.items,
        )

    order_summary = None
    if movement.order:
        ord_ = movement.order
        order_summary = OrderSummary(
            id=ord_.id,
            status=ord_.status,
            customer_name=ord_.customer.name if ord_.customer else None,
        )

    return StockMovementDetail(
        id=movement.id,
        created_at=movement.created_at,
        product=ProductSummary.model_validate(movement.product),
        quantity=movement.quantity,
        type=movement.type,
        invoice_id=movement.invoice_id,
        order_id=movement.order_id,
        invoice=invoice_detail,
        order=order_summary,
    )


@router.get("", response_model=list[StockMovementResponse])
def get_all(
    product_id: int | None = Query(None, description="Filter by product ID"),
    type: MovementType | None = Query(None, description="Filter by movement type"),
    date_from: datetime | None = Query(None, description="Filter movements on or after this datetime (ISO 8601)"),
    date_to: datetime | None = Query(None, description="Filter movements on or before this datetime (ISO 8601)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    movements = list_movements(
        db,
        product_id=product_id,
        movement_type=type,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return [_build_list_response(m) for m in movements]


@router.get("/{movement_id}", response_model=StockMovementDetail)
def get_one(movement_id: int, db: Session = Depends(get_db)):
    movement = get_movement(db, movement_id)
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock movement not found")
    return _build_detail_response(movement)
