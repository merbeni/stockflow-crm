from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_org_id, get_current_user
from app.core.errors import DomainError, NotFoundError
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

# Margen de tolerancia para "hasta": cubre husos horarios sin permitir rangos
# claramente absurdos hacia el futuro.
_MARGEN_FUTURO = timedelta(days=1)


def _validar_rango(date_from: datetime | None, date_to: datetime | None) -> None:
    """
    Comprueba que el rango de fechas tenga sentido.

    Sin esta validación, un rango invertido devolvía una lista vacía sin ningún
    aviso y parecía que simplemente no había movimientos.
    """
    if date_from and date_to and date_from > date_to:
        raise DomainError(
            'La fecha "desde" no puede ser posterior a la fecha "hasta". '
            "Corregí el rango e intentá de nuevo.",
            field="date_from",
        )

    # Solo se controla el extremo inicial: pedir movimientos a partir de una
    # fecha futura no tiene sentido, mientras que un "hasta" lejano es
    # simplemente un límite superior abierto.
    if date_from is not None:
        referencia = date_from if date_from.tzinfo else date_from.replace(tzinfo=timezone.utc)
        if referencia > datetime.now(timezone.utc) + _MARGEN_FUTURO:
            raise DomainError(
                'La fecha "desde" no puede estar en el futuro: los movimientos '
                "de stock son hechos ya ocurridos.",
                field="date_from",
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
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    _validar_rango(date_from, date_to)
    movements = list_movements(
        db,
        org_id,
        product_id=product_id,
        movement_type=type,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return [_build_list_response(m) for m in movements]


@router.get("/{movement_id}", response_model=StockMovementDetail)
def get_one(
    movement_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    movement = get_movement(db, movement_id, org_id)
    if not movement:
        raise NotFoundError("No encontramos ese movimiento de stock.")
    return _build_detail_response(movement)
