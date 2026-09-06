from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models.order import OrderItem
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.stock_rules import formatear_cantidad, validar_cantidad


def get_product(db: Session, product_id: int, organization_id: int) -> Product | None:
    return (
        db.query(Product)
        .filter(Product.id == product_id, Product.organization_id == organization_id)
        .first()
    )


def get_product_by_sku(db: Session, sku: str, organization_id: int) -> Product | None:
    return (
        db.query(Product)
        .filter(Product.sku == sku, Product.organization_id == organization_id)
        .first()
    )


def list_products(
    db: Session, organization_id: int, low_stock_only: bool = False
) -> list[Product]:
    query = db.query(Product).filter(Product.organization_id == organization_id)
    if low_stock_only:
        query = query.filter(Product.current_stock < Product.minimum_stock)
    return query.order_by(Product.name).all()


def create_product(db: Session, payload: ProductCreate, organization_id: int) -> Product:
    product = Product(**payload.model_dump(), organization_id=organization_id)
    db.add(product)
    db.flush()
    if float(product.current_stock) != 0:
        db.add(StockMovement(
            organization_id=organization_id,
            product_id=product.id,
            quantity=float(product.current_stock),
            type=MovementType.entry,
        ))
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    data = payload.model_dump(exclude_unset=True)

    # El flag efectivo es el que venga en el pedido o, si no viene, el ya guardado.
    permite_decimales = data.get("allow_decimal_stock", product.allow_decimal_stock)
    for campo in ("current_stock", "minimum_stock"):
        if data.get(campo) is not None:
            validar_cantidad(
                data[campo],
                permite_decimales=permite_decimales,
                nombre_producto=data.get("name", product.name),
                campo=campo,
            )

    # Al desactivar los decimales, el stock ya guardado tiene que ser entero.
    if data.get("allow_decimal_stock") is False and "current_stock" not in data:
        validar_cantidad(
            product.current_stock,
            permite_decimales=False,
            nombre_producto=product.name,
            campo="allow_decimal_stock",
        )

    new_stock = data.get("current_stock")
    if new_stock is not None:
        old_stock = float(product.current_stock)
        new_stock = float(new_stock)
        diff = new_stock - old_stock
        if diff != 0:
            # Store signed quantity so the UI can show +/- for adjustments
            db.add(StockMovement(
                organization_id=product.organization_id,
                product_id=product.id,
                quantity=diff,
                type=MovementType.adjustment,
            ))

    for field, value in data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


# ── borrado ───────────────────────────────────────────────────────────────────

def _historial_comercial(db: Session, product_ids: list[int]) -> dict[int, tuple[int, int]]:
    """
    Cuenta, por producto, el historial que impide eliminarlo.

    Se distingue el historial **comercial real** (líneas de pedido y movimientos
    originados en una factura o un pedido) de los movimientos **internos** que
    genera el propio sistema al dar de alta el producto o al ajustar su stock.
    Estos últimos no son operaciones del negocio y no deben bloquear el borrado.
    """
    if not product_ids:
        return {}

    pedidos = dict(
        db.query(OrderItem.product_id, func.count(OrderItem.id))
        .filter(OrderItem.product_id.in_(product_ids))
        .group_by(OrderItem.product_id)
        .all()
    )
    movimientos = dict(
        db.query(StockMovement.product_id, func.count(StockMovement.id))
        .filter(
            StockMovement.product_id.in_(product_ids),
            or_(
                StockMovement.invoice_id.isnot(None),
                StockMovement.order_id.isnot(None),
            ),
        )
        .group_by(StockMovement.product_id)
        .all()
    )
    return {pid: (pedidos.get(pid, 0), movimientos.get(pid, 0)) for pid in product_ids}


def _motivo_bloqueo(
    product: Product, lineas_pedido: int, movimientos_documentados: int
) -> str | None:
    if lineas_pedido:
        return (
            f"El producto figura en {lineas_pedido} línea(s) de pedido. "
            "Para conservar el historial de ventas no se puede eliminar: "
            "desactivalo en su lugar."
        )
    if movimientos_documentados:
        return (
            f"El producto tiene {movimientos_documentados} movimiento(s) de stock "
            "originados en facturas o pedidos. Para conservar la trazabilidad no "
            "se puede eliminar: desactivalo en su lugar."
        )
    if Decimal(str(product.current_stock)) != 0:
        return (
            f"Todavía quedan {formatear_cantidad(product.current_stock)} "
            "unidades en stock. Ajustá el stock a 0 antes de eliminar el producto."
        )
    return None


def deletability_map(db: Session, products: list[Product]) -> dict[int, tuple[bool, str | None]]:
    """Calcula en bloque si cada producto puede eliminarse (evita el N+1)."""
    historial = _historial_comercial(db, [p.id for p in products])
    resultado: dict[int, tuple[bool, str | None]] = {}
    for product in products:
        lineas, movimientos = historial.get(product.id, (0, 0))
        motivo = _motivo_bloqueo(product, lineas, movimientos)
        resultado[product.id] = (motivo is None, motivo)
    return resultado


def delete_product(db: Session, product: Product) -> None:
    """
    Elimina un producto que no tiene historial comercial.

    Los movimientos internos (alta y ajustes manuales) se borran en la misma
    transacción. Antes esto fallaba siempre: la relación declaraba
    ``passive_deletes=True`` mientras la clave foránea usaba
    ``ondelete="RESTRICT"``, de modo que la base rechazaba el borrado y ningún
    producto que alguna vez hubiera tenido un movimiento podía eliminarse.
    """
    puede, motivo = deletability_map(db, [product])[product.id]
    if not puede:
        raise DomainError(motivo, status_code=409)

    db.query(StockMovement).filter(
        StockMovement.product_id == product.id,
        StockMovement.invoice_id.is_(None),
        StockMovement.order_id.is_(None),
    ).delete(synchronize_session=False)

    db.delete(product)
    db.commit()
