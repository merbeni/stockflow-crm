"""
Reglas de integridad del stock compartidas por productos, facturas y pedidos.

Un producto unitario no puede tener existencias fraccionarias: "3.5 teclados"
no es una cantidad válida. Los artículos a granel (kg, litros, metros) sí,
y se identifican con el flag ``allow_decimal_stock``.
"""
from decimal import Decimal

from app.core.errors import DomainError


def admite_decimales(producto) -> bool:
    return bool(getattr(producto, "allow_decimal_stock", False))


def formatear_cantidad(cantidad: Decimal | float | int | None) -> str:
    """
    Devuelve la cantidad como la escribiría una persona, para usarla dentro de
    los mensajes de error.

    ``Decimal.normalize`` sirve para quitar los ceros de relleno («1.500» →
    «1.5»), pero en los números redondos grandes cambia a notación científica:
    el stock «1000.000» que guarda la base se convierte en «1E+3». Un mensaje
    que dice "quedan 1E+3" no se entiende, así que se recorta el exponente.
    """
    if cantidad is None:
        return "0"
    # El formato "f" expande el exponente que deja normalize() y no reintroduce
    # los ceros de relleno: 1E+3 → «1000», 1.500 → «1.5».
    return format(Decimal(str(cantidad)).normalize(), "f")


def validar_cantidad(
    cantidad: Decimal | float | None,
    *,
    permite_decimales: bool,
    nombre_producto: str,
    campo: str | None = None,
) -> None:
    """
    Verifica que la cantidad sea entera cuando el producto no admite decimales.

    Lanza ``DomainError`` con un mensaje orientado al usuario, sin exponer
    nombres de columnas ni identificadores internos.
    """
    if cantidad is None or permite_decimales:
        return

    valor = Decimal(str(cantidad))
    if valor == valor.to_integral_value():
        return

    raise DomainError(
        f'El producto «{nombre_producto}» se maneja en unidades enteras, '
        f"así que {formatear_cantidad(valor)} no es una cantidad válida. "
        "Si se vende a granel (por kilo, litro o metro), habilitá la opción "
        '"Admite stock decimal" en la ficha del producto.',
        field=campo,
    )
