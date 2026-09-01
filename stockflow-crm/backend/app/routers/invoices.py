import logging

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File, status
from google.genai.errors import ServerError
from sqlalchemy.orm import Session

from app.core.deps import get_current_org_id, get_current_user
from app.core.errors import DomainError, NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.schemas.invoice import (
    InvoiceConfirmPayload,
    InvoiceProcessResponse,
    InvoiceResponse,
)
from app.services.email_service import send_low_stock_alert
from app.services.invoice.gemini_service import (
    ALLOWED_MIME_TYPES,
    contenido_coincide_con_tipo,
)
from app.services.invoice.invoice_service import (
    confirm_invoice,
    get_invoice,
    list_invoices,
    process_invoice,
    reject_invoice,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
    dependencies=[Depends(get_current_user)],
)

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
_FORMATOS_LEGIBLES = "PDF, JPG, PNG o WEBP"


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
    file: UploadFile = File(..., description="Archivo de la factura (PDF, JPG, PNG o WEBP)"),
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise DomainError(
            f"El formato del archivo no está permitido. Subí la factura en "
            f"{_FORMATOS_LEGIBLES}.",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            field="file",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise DomainError(
            "El archivo supera el límite de 20 MB. Probá con una imagen de menor "
            "resolución o con el PDF original.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            field="file",
        )

    # El content_type lo declara el cliente: se verifica el contenido real para
    # que cambiar la extensión de un archivo no alcance para saltear el control.
    if not contenido_coincide_con_tipo(file_bytes, file.content_type):
        raise DomainError(
            "El archivo está dañado o su contenido no coincide con su extensión. "
            f"Subí la factura en {_FORMATOS_LEGIBLES}.",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            field="file",
        )

    try:
        return process_invoice(db, file_bytes, file.content_type, org_id)
    except ServerError as exc:
        if exc.code == 503:
            raise DomainError(
                "gemini_unavailable",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        logger.exception("Error al comunicarse con Gemini")
        raise DomainError(
            "El servicio de lectura automática no está disponible en este momento. "
            "Intentá de nuevo en unos minutos.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    except ValueError as exc:
        # El texto original puede incluir la respuesta cruda del modelo: al log.
        logger.warning("Respuesta no interpretable de Gemini: %s", exc)
        raise DomainError(
            "No pudimos interpretar el documento. Verificá que sea una factura "
            "legible e intentá nuevamente.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            field="file",
        )


@router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
def confirm(
    invoice_id: int,
    payload: InvoiceConfirmPayload,
    background_tasks: BackgroundTasks,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice, low_stock_products = confirm_invoice(db, invoice_id, payload, org_id)

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
def reject(
    invoice_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return _invoice_to_response(reject_invoice(db, invoice_id, org_id))


@router.get("", response_model=list[InvoiceResponse])
def get_all(
    org_id: int = Depends(get_current_org_id), db: Session = Depends(get_db)
):
    return [_invoice_to_response(inv) for inv in list_invoices(db, org_id)]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_one(
    invoice_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    invoice = get_invoice(db, invoice_id, org_id)
    if not invoice:
        raise NotFoundError("No encontramos esa factura.")
    return _invoice_to_response(invoice)
