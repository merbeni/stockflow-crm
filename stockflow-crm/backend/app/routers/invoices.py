from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, status
from google.genai.errors import ServerError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.invoice import (
    InvoiceConfirmPayload,
    InvoiceProcessResponse,
    InvoiceResponse,
)
from app.services.email_service import send_low_stock_alert
from app.services.invoice.gemini_service import ALLOWED_MIME_TYPES
from app.services.invoice.invoice_service import (
    confirm_invoice,
    get_invoice,
    list_invoices,
    process_invoice,
    reject_invoice,
)

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
    dependencies=[Depends(get_current_user)],
)

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _invoice_to_response(invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        supplier_id=invoice.supplier_id,
        supplier_name=invoice.supplier.name if invoice.supplier else None,
        date=invoice.date,
        file_url=invoice.file_url,
        status=invoice.status,
        created_at=invoice.created_at,
        items=invoice.items,
    )


@router.post("/process", response_model=InvoiceProcessResponse, status_code=status.HTTP_201_CREATED)
async def process(
    file: UploadFile = File(..., description="Invoice file (PDF, JPG, PNG)"),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. "
                   f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 20 MB limit",
        )

    try:
        return process_invoice(db, file_bytes, file.content_type)
    except ServerError as exc:
        if exc.code == 503:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="gemini_unavailable",
            )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
def confirm(
    invoice_id: int,
    payload: InvoiceConfirmPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        invoice, low_stock_products = confirm_invoice(db, invoice_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    for product in low_stock_products:
        background_tasks.add_task(
            send_low_stock_alert,
            to_email=current_user.email,
            product_name=product.name,
            product_sku=product.sku,
            current_stock=float(product.current_stock),
            minimum_stock=float(product.minimum_stock),
        )

    return _invoice_to_response(invoice)


@router.post("/{invoice_id}/reject", response_model=InvoiceResponse)
def reject(invoice_id: int, db: Session = Depends(get_db)):
    try:
        invoice = reject_invoice(db, invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _invoice_to_response(invoice)


@router.get("", response_model=list[InvoiceResponse])
def get_all(db: Session = Depends(get_db)):
    return [_invoice_to_response(inv) for inv in list_invoices(db)]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_one(invoice_id: int, db: Session = Depends(get_db)):
    invoice = get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return _invoice_to_response(invoice)
