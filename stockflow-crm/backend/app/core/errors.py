"""
Contrato de errores de la API.

Toda respuesta de error devuelve el mismo formato, de modo que el frontend
nunca reciba estructuras inesperadas:

    {
        "detail": "<mensaje legible en español>",   # SIEMPRE un string
        "errors": {"<campo>": "<mensaje>"}          # opcional, para pintar inputs
    }

El motivo es doble:

1.  FastAPI devuelve por defecto ``detail`` como una *lista de objetos* en los
    errores 422. El frontend lo renderizaba directamente y React lanzaba
    "Objects are not valid as a React child", dejando la pantalla en blanco.
2.  Los detalles técnicos (constraints, tablas, tracebacks) no deben viajar al
    navegador. Se registran del lado del servidor y el usuario recibe un
    mensaje de negocio.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """
    Error de regla de negocio con un mensaje apto para el usuario final.

    ``message`` es lo único que viaja al navegador. ``internal`` guarda el
    detalle técnico, que solo se escribe en el log del servidor.
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        internal: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.status_code = status_code
        self.internal = internal


class NotFoundError(DomainError):
    """El recurso no existe o pertenece a otra organización."""

    def __init__(self, message: str, *, internal: str | None = None) -> None:
        super().__init__(
            message, status_code=status.HTTP_404_NOT_FOUND, internal=internal
        )


# ── etiquetas legibles por campo ──────────────────────────────────────────────

FIELD_LABELS: dict[str, str] = {
    "address": "dirección",
    "allow_decimal_stock": "admite stock decimal",
    "contact_name": "nombre de contacto",
    "current_stock": "stock actual",
    "customer_id": "cliente",
    "date_from": "fecha desde",
    "date_to": "fecha hasta",
    "description": "descripción",
    "email": "correo electrónico",
    "full_name": "nombre y apellido",
    "invoice_item_id": "línea de la factura",
    "items": "ítems",
    "minimum_stock": "stock mínimo",
    "name": "nombre",
    "new_product": "producto nuevo",
    "new_supplier": "proveedor nuevo",
    "organization_name": "nombre de la organización",
    "password": "contraseña",
    "phone": "teléfono",
    "price": "precio",
    "product_id": "producto",
    "quantity": "cantidad",
    "role": "rol",
    "sku": "SKU",
    "status": "estado",
    "supplier_id": "proveedor",
    "supplier_sku": "SKU del proveedor",
    "token": "token",
    "unit_price": "precio unitario",
}


def _field_path(loc: tuple) -> str:
    """Convierte la tupla ``loc`` de Pydantic en una ruta de campo del formulario."""
    parts = [
        str(part)
        for part in loc
        if part not in ("body", "query", "path", "header", "cookie")
    ]
    return ".".join(parts) if parts else "__general__"


def _field_label(field: str) -> str:
    """Etiqueta legible del último segmento de la ruta (ignora los índices)."""
    segments = [seg for seg in field.split(".") if not seg.isdigit()]
    leaf = segments[-1] if segments else field
    return FIELD_LABELS.get(leaf, leaf.replace("_", " "))


def _translate(error: dict) -> str:
    """Traduce un error de validación de Pydantic a un mensaje en español."""
    err_type = error.get("type", "")
    ctx = error.get("ctx") or {}
    raw_msg = str(error.get("msg", ""))

    if err_type == "missing":
        return "Este campo es obligatorio."
    if err_type in ("string_too_short", "too_short"):
        minimum = ctx.get("min_length", ctx.get("min_length", 1))
        return f"Debe tener al menos {minimum} caracteres."
    if err_type in ("string_too_long", "too_long"):
        return f"No puede superar los {ctx.get('max_length')} caracteres."
    if err_type == "string_pattern_mismatch":
        return "El formato ingresado no es válido."
    if err_type == "greater_than":
        return f"Debe ser mayor que {ctx.get('gt')}."
    if err_type == "greater_than_equal":
        return f"Debe ser mayor o igual a {ctx.get('ge')}."
    if err_type == "less_than":
        return f"Debe ser menor que {ctx.get('lt')}."
    if err_type == "less_than_equal":
        return f"Debe ser menor o igual a {ctx.get('le')}."
    if err_type == "decimal_max_places":
        places = ctx.get("decimal_places")
        if places == 0:
            return "Debe ser un número entero."
        return f"No puede tener más de {places} decimales."
    if err_type in (
        "int_parsing",
        "int_type",
        "float_parsing",
        "float_type",
        "decimal_parsing",
        "decimal_type",
    ):
        return "Debe ser un número válido."
    if err_type in ("bool_parsing", "bool_type"):
        return "Debe ser verdadero o falso."
    if err_type in ("date_parsing", "date_type", "datetime_parsing", "datetime_type"):
        return "Debe ser una fecha válida."
    if err_type in ("string_type", "str_type"):
        return "Debe ser un texto."
    if err_type in ("enum", "literal_error"):
        expected = ctx.get("expected")
        if expected:
            return f"Valor no permitido. Opciones válidas: {expected}."
        return "Valor no permitido."
    if err_type == "json_invalid":
        return "El formato enviado no es válido."
    if err_type in ("list_type", "dict_type", "model_attributes_type"):
        return "El formato enviado no es válido."

    # EmailStr en Pydantic v2 reporta type "value_error".
    if "valid email address" in raw_msg:
        return "No es una dirección de correo válida."

    # Los validadores propios lanzan ValueError con el texto ya en español;
    # Pydantic le antepone "Value error, ".
    if raw_msg.startswith("Value error, "):
        return raw_msg[len("Value error, ") :]

    return "El valor ingresado no es válido."


def build_validation_response(errors: list[dict]) -> dict:
    """Arma el cuerpo de la respuesta 422 a partir de los errores de Pydantic."""
    field_errors: dict[str, str] = {}
    messages: list[str] = []

    for error in errors:
        field = _field_path(error.get("loc", ()))
        message = _translate(error)
        # Se conserva el primer error de cada campo: es el más específico.
        if field in field_errors:
            continue
        field_errors[field] = message

        label = _field_label(field)
        if field == "__general__":
            messages.append(message)
        else:
            messages.append(f"{label.capitalize()}: {message}")

    if not messages:
        detail = "Los datos enviados no son válidos."
    elif len(messages) == 1:
        detail = messages[0]
    else:
        detail = "Revisá los siguientes campos — " + " ".join(messages)

    return {"detail": detail, "errors": field_errors}


# ── handlers ──────────────────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Registra los handlers que garantizan el formato uniforme de errores."""

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=build_validation_response(exc.errors()),
        )

    @app.exception_handler(DomainError)
    async def _domain_handler(_: Request, exc: DomainError):
        if exc.internal:
            logger.warning("Regla de negocio incumplida: %s", exc.internal)
        body: dict = {"detail": exc.message, "errors": {}}
        if exc.field:
            body["errors"] = {exc.field: exc.message}
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_: Request, exc: StarletteHTTPException):
        # Normaliza detail a string: nunca debe llegar una lista o un dict al frontend.
        detail = exc.detail if isinstance(exc.detail, str) else "Ocurrió un error."
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail, "errors": {}},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_handler(_: Request, exc: IntegrityError):
        # El texto original menciona tablas y constraints: solo va al log.
        logger.warning("Violación de integridad referencial: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": (
                    "La operación no se puede completar porque hay información "
                    "relacionada que depende de este registro."
                ),
                "errors": {},
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy_handler(_: Request, exc: SQLAlchemyError):
        logger.exception("Error de base de datos: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Ocurrió un error al acceder a los datos. Intentá nuevamente.",
                "errors": {},
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception):
        logger.exception("Error no controlado: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Ocurrió un error inesperado. Por favor intentá nuevamente.",
                "errors": {},
            },
        )
