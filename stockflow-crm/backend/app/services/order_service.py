from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import DomainError, NotFoundError
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.schemas.order import OrderCreate, OrderItemAdd, OrderItemResponse, OrderResponse
from app.services.stock_rules import formatear_cantidad, validar_cantidad

# Valid status transitions
_TRANSITIONS: dict[OrderStatus, OrderStatus] = {
    OrderStatus.pending: OrderStatus.processing,
    OrderStatus.processing: OrderStatus.shipped,
    OrderStatus.shipped: OrderStatus.delivered,
}

_ESTADOS_ES = {
    OrderStatus.pending: "pendiente",
    OrderStatus.processing: "en preparación",
    OrderStatus.shipped: "enviado",
    OrderStatus.delivered: "entregado",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_order(db: Session, order_id: int, organization_id: int) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.organization_id == organization_id)
        .options(
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
    )
    return db.scalars(stmt).first()


def _require_order(db: Session, order_id: int, organization_id: int) -> Order:
    order = _load_order(db, order_id, organization_id)
    if not order:
        raise NotFoundError("No encontramos ese pedido.")
    return order


def _build_response(order: Order) -> OrderResponse:
    items = []
    total = Decimal("0")
    for oi in order.items:
        qty = Decimal(str(oi.quantity))
        price = Decimal(str(oi.unit_price))
        items.append(OrderItemResponse(
            id=oi.id,
            product_id=oi.product_id,
            product_sku=oi.product.sku,
            product_name=oi.product.name,
            quantity=qty,
            unit_price=price,
        ))
        total += qty * price
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        customer_name=order.customer.name,
        customer_email=order.customer.email,
        status=order.status,
        created_at=order.created_at,
        items=items,
        total=total,
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

def list_orders(db: Session, organization_id: int) -> list[OrderResponse]:
    stmt = (
        select(Order)
        .where(Order.organization_id == organization_id)
        .options(
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
        .order_by(Order.created_at.desc())
    )
    orders = list(db.scalars(stmt).unique())
    return [_build_response(o) for o in orders]


def get_order(db: Session, order_id: int, organization_id: int) -> OrderResponse | None:
    order = _load_order(db, order_id, organization_id)
    return _build_response(order) if order else None


def create_order(db: Session, payload: OrderCreate, organization_id: int) -> OrderResponse:
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == payload.customer_id,
            Customer.organization_id == organization_id,
        )
        .first()
    )
    if not customer:
        raise NotFoundError("No encontramos ese cliente.")

    order = Order(
        customer_id=payload.customer_id,
        organization_id=organization_id,
        status=OrderStatus.pending,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _build_response(_load_order(db, order.id, organization_id))


def delete_order(db: Session, order_id: int, organization_id: int) -> None:
    order = _require_order(db, order_id, organization_id)
    if order.status != OrderStatus.pending:
        raise DomainError(
            f"El pedido ya está {_ESTADOS_ES[order.status]}, así que no se puede "
            "eliminar. Solo se pueden borrar los pedidos pendientes."
        )
    db.delete(order)
    db.commit()


# ── Items ─────────────────────────────────────────────────────────────────────

def add_item(
    db: Session, order_id: int, payload: OrderItemAdd, organization_id: int
) -> OrderResponse:
    order = _require_order(db, order_id, organization_id)
    if order.status != OrderStatus.pending:
        raise DomainError(
            "Solo se pueden agregar productos a un pedido que siga pendiente."
        )

    product = (
        db.query(Product)
        .filter(
            Product.id == payload.product_id,
            Product.organization_id == organization_id,
        )
        .first()
    )
    if not product:
        raise NotFoundError("No encontramos ese producto.")
    if not product.is_active:
        raise DomainError(
            f"El producto «{product.name}» está desactivado y no se puede agregar "
            "a un pedido.",
            field="product_id",
        )

    validar_cantidad(
        payload.quantity,
        permite_decimales=product.allow_decimal_stock,
        nombre_producto=product.name,
        campo="quantity",
    )

    # El mismo producto puede estar ya en otra línea del pedido, así que lo
    # disponible es el stock menos lo que este pedido reserva. Comparar solo
    # contra el stock dejaba armar pedidos que después no se podían confirmar.
    ya_reservado = sum(
        float(oi.quantity) for oi in order.items if oi.product_id == payload.product_id
    )
    disponible = float(product.current_stock) - ya_reservado
    if float(payload.quantity) > disponible:
        detalle = f"quedan {formatear_cantidad(product.current_stock)}"
        if ya_reservado:
            detalle += f", este pedido ya reserva {formatear_cantidad(ya_reservado)}"
        raise DomainError(
            f"No hay stock suficiente de «{product.name}»: {detalle} y se piden "
            f"{formatear_cantidad(payload.quantity)}.",
            field="quantity",
        )

    db.add(OrderItem(
        order_id=order_id,
        product_id=payload.product_id,
        quantity=float(payload.quantity),
        unit_price=float(payload.unit_price),
    ))
    db.commit()
    return _build_response(_load_order(db, order_id, organization_id))


def remove_item(
    db: Session, order_id: int, item_id: int, organization_id: int
) -> OrderResponse:
    order = _require_order(db, order_id, organization_id)
    if order.status != OrderStatus.pending:
        raise DomainError(
            "Solo se pueden quitar productos de un pedido que siga pendiente."
        )

    item = db.get(OrderItem, item_id)
    if not item or item.order_id != order_id:
        raise NotFoundError("No encontramos esa línea del pedido.")

    db.delete(item)
    db.commit()
    return _build_response(_load_order(db, order_id, organization_id))


# ── Status transition ─────────────────────────────────────────────────────────

def advance_status(db: Session, order_id: int, organization_id: int) -> OrderResponse:
    order = _require_order(db, order_id, organization_id)

    next_status = _TRANSITIONS.get(order.status)
    if not next_status:
        raise DomainError(
            f"El pedido ya está {_ESTADOS_ES[order.status]}: no quedan más "
            "estados por avanzar."
        )

    # pendiente → en preparación: descuenta stock y registra las salidas.
    if order.status == OrderStatus.pending:
        if not order.items:
            raise DomainError(
                "No se puede confirmar un pedido sin productos. Agregá al menos uno."
            )
        # Un producto puede aparecer en varias líneas, así que primero se suma
        # todo lo que pide el pedido y recién después se compara con el stock.
        # Validar mientras se descontaba hacía que el mensaje informara un stock
        # ya modificado en memoria («quedan 0») distinto del que muestra la
        # pantalla de productos.
        requerido: dict[int, float] = {}
        for oi in order.items:
            requerido[oi.product_id] = requerido.get(oi.product_id, 0.0) + float(oi.quantity)

        for product_id, total in requerido.items():
            product = db.get(Product, product_id)
            if float(product.current_stock) < total:
                raise DomainError(
                    f"No hay stock suficiente de «{product.name}»: quedan "
                    f"{formatear_cantidad(product.current_stock)} y el pedido "
                    f"requiere {formatear_cantidad(total)}."
                )

        for oi in order.items:
            product = db.get(Product, oi.product_id)
            qty = float(oi.quantity)
            product.current_stock = float(product.current_stock) - qty
            db.add(StockMovement(
                organization_id=organization_id,
                product_id=product.id,
                quantity=qty,
                type=MovementType.exit,
                order_id=order_id,
            ))

    order.status = next_status
    db.commit()
    return _build_response(_load_order(db, order_id, organization_id))
