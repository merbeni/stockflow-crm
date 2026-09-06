"""
Validadores reutilizables de los esquemas, con mensajes en español.

Los `ValueError` que se lanzan acá llegan al usuario tal cual: el handler de
``app.core.errors`` les quita el prefijo "Value error, " que agrega Pydantic.
"""
import re
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import AfterValidator, BeforeValidator, EmailStr, Field

_RE_TELEFONO = re.compile(r"^[0-9+\-\s().]{6,}$")
_RE_SKU = re.compile(r"^[A-Za-z0-9._\-/]+$")


def _recortar(valor):
    """Quita espacios sobrantes antes de validar longitudes."""
    return valor.strip() if isinstance(valor, str) else valor


def _vacio_a_none(valor):
    """
    Normaliza un texto opcional: recorta y convierte "" en None.

    Se aplica sobre el tipo opcional completo, porque las restricciones de
    longitud solo pueden ir sobre la rama `str`: Pydantic falla al intentar
    aplicar `max_length` a un valor `None`.
    """
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def _no_vacio(valor: str) -> str:
    if not valor or not valor.strip():
        raise ValueError("No puede estar vacío.")
    return valor


def _normalizar_correo(valor):
    """
    Pasa el correo a minúsculas.

    El correo no distingue mayúsculas: sin esto, "Ana@test.com" y "ana@test.com"
    generaban dos cuentas distintas, y quien se registraba con mayúsculas no
    podía volver a entrar escribiéndolo en minúsculas.
    """
    return valor.strip().lower() if isinstance(valor, str) else valor


def _sin_digitos(valor: str) -> str:
    if any(caracter.isdigit() for caracter in valor):
        raise ValueError("No puede contener números.")
    return valor


def _telefono_valido(valor: str) -> str:
    if not _RE_TELEFONO.match(valor):
        raise ValueError(
            "Debe tener al menos 6 dígitos y solo puede incluir números, "
            "espacios y los signos + - ( ) ."
        )
    if sum(caracter.isdigit() for caracter in valor) < 6:
        raise ValueError("Debe incluir al menos 6 dígitos.")
    return valor


def _sku_valido(valor: str) -> str:
    if not _RE_SKU.match(valor):
        raise ValueError(
            "Solo puede contener letras, números y los signos . _ - / (sin espacios)."
        )
    return valor


def _password_segura(valor: str) -> str:
    if len(valor) < 8:
        raise ValueError("Debe tener al menos 8 caracteres.")
    if not any(caracter.isalpha() for caracter in valor):
        raise ValueError("Debe incluir al menos una letra.")
    if not any(caracter.isdigit() for caracter in valor):
        raise ValueError("Debe incluir al menos un número.")
    return valor


# ── tipos anotados ────────────────────────────────────────────────────────────

def TextoObligatorio(max_length: int = 255):
    """Texto que no puede quedar vacío ni contener solo espacios."""
    return Annotated[
        str,
        BeforeValidator(_recortar),
        Field(min_length=1, max_length=max_length),
        AfterValidator(_no_vacio),
    ]


def TextoOpcional(max_length: int = 255):
    """Texto opcional: se recorta y "" equivale a no informarlo."""
    return Annotated[
        Optional[Annotated[str, Field(max_length=max_length)]],
        BeforeValidator(_vacio_a_none),
    ]


def NombrePersona(max_length: int = 255):
    """
    Nombre de una persona: no admite dígitos.

    Se aplica a nombres de contacto y de usuarios. **No** se usa en el nombre de
    un producto, donde los números son legítimos ("Coca Cola 500ml").
    """
    return Annotated[
        str,
        BeforeValidator(_recortar),
        Field(min_length=2, max_length=max_length),
        AfterValidator(_no_vacio),
        AfterValidator(_sin_digitos),
    ]


def NombrePersonaOpcional(max_length: int = 255):
    return Annotated[
        Optional[
            Annotated[
                str,
                Field(min_length=2, max_length=max_length),
                AfterValidator(_sin_digitos),
            ]
        ],
        BeforeValidator(_vacio_a_none),
    ]


Telefono = Annotated[
    str,
    BeforeValidator(_recortar),
    Field(max_length=50),
    AfterValidator(_no_vacio),
    AfterValidator(_telefono_valido),
]

TelefonoOpcional = Annotated[
    Optional[
        Annotated[str, Field(max_length=50), AfterValidator(_telefono_valido)]
    ],
    BeforeValidator(_vacio_a_none),
]

Sku = Annotated[
    str,
    BeforeValidator(_recortar),
    Field(min_length=1, max_length=100),
    AfterValidator(_no_vacio),
    AfterValidator(_sku_valido),
]

Password = Annotated[str, AfterValidator(_password_segura)]

CorreoElectronico = Annotated[EmailStr, BeforeValidator(_normalizar_correo)]

CorreoOpcional = Annotated[
    Optional[EmailStr], BeforeValidator(lambda v: _normalizar_correo(v) or None)
]

# ── importes y cantidades ─────────────────────────────────────────────────────
# Los límites replican el tipo de la columna en la base: sin ellos, un valor
# desmedido llegaba hasta PostgreSQL y volvía como error 500 en lugar de un
# mensaje de validación.

Importe = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
"""Monto en pesos. Coincide con Numeric(10,2): hasta 99.999.999,99."""

Cantidad = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=3)]
"""Cantidad de stock. Coincide con Numeric(10,3): hasta 9.999.999,999."""

CantidadPositiva = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=3)]
"""Cantidad que además debe ser mayor que cero (líneas de factura y pedidos)."""
