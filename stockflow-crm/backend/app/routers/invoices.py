import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File, status
from google.genai.errors import APIError, ClientError, ServerError
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
from app.models.invoice import InvoiceStatus
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
    sugerencias_de_factura,
)

logger = logging.getLogger(__name__)

# Se muestra tal cual si el reintento automático del frontend vuelve a fallar,
# así que está escrito para una persona y no como código interno.
MENSAJE_SERVICIO_OCUPADO = (
    "El servicio de lectura automática está recibiendo más pedidos de los que "
    "puede atender. Esperá unos minutos y volvé a intentar."
)

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
    dependencies=[Depends(get_current_user)],
)

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
_FORMATOS_LEGIBLES = "PDF, JPG, PNG o WEBP"


def _invoice_to_response(invoice, db: Session = None, org_id: int = None) -> InvoiceResponse:
    """
    Arma la respuesta de una factura.

    En las que siguen pendientes se recalcula el emparejado automático: la
    pantalla invita a dejar la revisión para después, y sin esto volver más
    tarde significaba encontrar todas las líneas en blanco y rehacer a mano lo
    que el sistema ya había resuelto. En las confirmadas o rechazadas no
    corresponde: la decisión ya está tomada.
    """
    respuesta = InvoiceResponse(
        id=invoice.id,
        supplier_id=invoice.supplier_id,
        supplier_name=invoice.supplier.name if invoice.supplier else None,
        date=invoice.date,
        file_url=invoice.file_url,
        status=invoice.status,
        created_at=invoice.created_at,
        items=invoice.items,
    )
    if db is None or invoice.status != InvoiceStatus.pending:
        return respuesta

    sugerencias, skus = sugerencias_de_factura(db, invoice, org_id)
    respuesta.supplier_product_skus = skus
    for item in respuesta.items:
        producto_id, producto_nombre, sku = sugerencias.get(item.id, (None, None, None))
        item.suggested_product_id = producto_id
        item.suggested_product_name = producto_nombre
        item.suggested_supplier_sku = sku
    return respuesta


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
            # El 503 es la señal de "volvé a intentar": el frontend reintenta
            # solo al recibirlo. El mensaje igual tiene que estar escrito para
            # una persona, porque es lo que se muestra si el reintento falla.
            raise DomainError(
                MENSAJE_SERVICIO_OCUPADO,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        logger.exception("Error al comunicarse con Gemini")
        raise DomainError(
            "El servicio de lectura automática no está disponible en este momento. "
            "Intentá de nuevo en unos minutos.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    except ClientError as exc:
        # Gemini responde 4xx cuando el pedido en sí no le sirve. Sin este bloque
        # la excepción escapaba y el usuario recibía un 500: un PDF corrupto o
        # sin páginas terminaba reportado como una falla del sistema, cuando el
        # problema estaba en el archivo y él podía resolverlo.
        if exc.code == 429:
            # Cuota agotada. Es el mismo caso de "volvé a intentar" que el 503,
            # así que se reusa ese código y el frontend reintenta solo.
            logger.warning("Cuota de Gemini agotada")
            raise DomainError(
                MENSAJE_SERVICIO_OCUPADO,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if exc.code in (400, 422):
            logger.info("Gemini no pudo leer el documento: %s", exc)
            raise DomainError(
                "No pudimos leer el archivo: puede estar dañado, vacío o "
                "protegido con contraseña. Abrilo para comprobar que se ve bien "
                "y volvé a subirlo, o probá con una foto del comprobante.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                field="file",
            )
        # 401 y 403 son credenciales mal configuradas: problema nuestro, no del
        # usuario, así que no se le pide que corrija nada.
        logger.exception("Gemini rechazó la petición")
        raise DomainError(
            "El servicio de lectura automática no está disponible en este "
            "momento. Intentá de nuevo en unos minutos.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    except (httpx.TransportError, APIError) as exc:
        # Un corte de red camino a Google, un tiempo de espera agotado o
        # cualquier fallo de transporte no son ni ServerError ni ClientError: se
        # escapaban de los bloques de arriba y llegaban al usuario como un 500
        # genérico. Es el mismo caso de "volvé a intentar" que el 503, así que
        # se responde igual y el frontend reintenta solo.
        logger.warning("Fallo de conexión con Gemini: %s", exc)
        raise DomainError(
            MENSAJE_SERVICIO_OCUPADO,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
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
    # Sin `db`: el listado no calcula sugerencias. Hacerlo obligaría a consultar
    # la base por cada línea de cada factura pendiente, y solo hacen falta al
    # abrir una para revisarla.
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
    return _invoice_to_response(invoice, db, org_id)
