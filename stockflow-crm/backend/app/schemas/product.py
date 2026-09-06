from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.schemas.validators import (
    Cantidad,
    Importe,
    Sku,
    TextoObligatorio,
    TextoOpcional,
)


def _validar_decimales(current_stock, minimum_stock, permite_decimales: bool) -> None:
    """Rechaza cantidades fraccionarias en productos que se venden por unidad."""
    if permite_decimales:
        return
    for valor in (current_stock, minimum_stock):
        if valor is None:
            continue
        cantidad = Decimal(str(valor))
        if cantidad != cantidad.to_integral_value():
            raise ValueError(
                "Este producto se maneja en unidades enteras. Marcá "
                '"Admite stock decimal" si se vende a granel (kilos, litros o metros).'
            )


class ProductCreate(BaseModel):
    sku: Sku
    # A diferencia del nombre de una persona, el de un producto sí admite
    # números: "Coca Cola 500ml" es perfectamente válido.
    name: TextoObligatorio(255)
    description: TextoOpcional(2000) = None
    price: Importe
    current_stock: Cantidad = Decimal("0")
    minimum_stock: Cantidad = Decimal("0")
    allow_decimal_stock: bool = False

    @model_validator(mode="after")
    def _revisar_decimales(self):
        _validar_decimales(self.current_stock, self.minimum_stock, self.allow_decimal_stock)
        return self


class ProductUpdate(BaseModel):
    sku: Sku | None = None
    name: TextoObligatorio(255) | None = None
    description: TextoOpcional(2000) = None
    price: Importe | None = None
    current_stock: Cantidad | None = None
    minimum_stock: Cantidad | None = None
    allow_decimal_stock: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _revisar_decimales(self):
        # Solo se puede decidir acá si el propio pedido fija el flag; cuando no
        # viene, la comprobación la hace el servicio con el valor ya guardado.
        if self.allow_decimal_stock is not None:
            _validar_decimales(
                self.current_stock, self.minimum_stock, self.allow_decimal_stock
            )
        return self


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    description: str | None
    price: Decimal
    current_stock: Decimal
    minimum_stock: Decimal
    allow_decimal_stock: bool
    is_active: bool
    created_at: datetime
    # Lo calcula el servicio: indica si el producto puede eliminarse y, si no,
    # por qué. Permite deshabilitar el botón en lugar de fallar al pulsarlo.
    can_delete: bool = False
    delete_blocked_reason: str | None = None

    @computed_field
    @property
    def low_stock(self) -> bool:
        return self.current_stock < self.minimum_stock

    model_config = {"from_attributes": True}
