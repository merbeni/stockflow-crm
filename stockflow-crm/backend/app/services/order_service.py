from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.schemas.order import OrderCreate, OrderItemAdd, OrderItemResponse, OrderResponse

# Valid status transitions
_TRANSITIONS: dict[OrderStatus, OrderStatus] = {
    OrderStatus.pending: OrderStatus.processing,
    OrderStatus.processing: OrderStatus.shipped,
    OrderStatus.shipped: OrderStatus.delivered,
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_order(db: Session, order_id: int) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
    )
    return db.scalars(stmt).first()


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

def list_orders(db: Session) -> list[OrderResponse]:
    stmt = (
        select(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
        .order_by(Order.created_at.desc())
    )
    orders = list(db.scalars(stmt).unique())
    return [_build_response(o) for o in orders]


def get_order(db: Session, order_id: int) -> OrderResponse | None:
    order = _load_order(db, order_id)
    return _build_response(order) if order else None


def create_order(db: Session, payload: OrderCreate) -> OrderResponse:
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise ValueError(f"Customer {payload.customer_id} not found")

    order = Order(customer_id=payload.customer_id, status=OrderStatus.pending)
    db.add(order)
    db.commit()
    db.refresh(order)
    return _build_response(_load_order(db, order.id))


def delete_order(db: Session, order_id: int) -> None:
    order = db.get(Order, order_id)
    if not order:
        raise ValueError("Order not found")
    if order.status != OrderStatus.pending:
        raise ValueError("Only pending orders can be deleted")
    db.delete(order)
    db.commit()


# ── Items ─────────────────────────────────────────────────────────────────────

def add_item(db: Session, order_id: int, payload: OrderItemAdd) -> OrderResponse:
    order = _load_order(db, order_id)
    if not order:
        raise ValueError("Order not found")
    if order.status != OrderStatus.pending:
        raise ValueError("Items can only be added to pending orders")

    product = db.get(Product, payload.product_id)
    if not product:
        raise ValueError(f"Product {payload.product_id} not found")
    if not product.is_active:
        raise ValueError(f"'{product.name}' is deactivated and cannot be added to orders")
    if float(payload.quantity) > float(product.current_stock):
        raise ValueError(
            f"Insufficient stock for '{product.name}': "
            f"available {float(product.current_stock)}, requested {float(payload.quantity)}"
        )

    db.add(OrderItem(
        order_id=order_id,
        product_id=payload.product_id,
        quantity=float(payload.quantity),
        unit_price=float(payload.unit_price),
    ))
    db.commit()
    return _build_response(_load_order(db, order_id))


def remove_item(db: Session, order_id: int, item_id: int) -> OrderResponse:
    order = _load_order(db, order_id)
    if not order:
        raise ValueError("Order not found")
    if order.status != OrderStatus.pending:
        raise ValueError("Items can only be removed from pending orders")

    item = db.get(OrderItem, item_id)
    if not item or item.order_id != order_id:
        raise ValueError("Order item not found")

    db.delete(item)
    db.commit()
    return _build_response(_load_order(db, order_id))


# ── Status transition ─────────────────────────────────────────────────────────

def advance_status(db: Session, order_id: int) -> OrderResponse:
    order = _load_order(db, order_id)
    if not order:
        raise ValueError("Order not found")

    next_status = _TRANSITIONS.get(order.status)
    if not next_status:
        raise ValueError(f"Order is already {order.status.value} — no further transitions")

    # pending → processing: deduct stock and create exit movements
    if order.status == OrderStatus.pending:
        if not order.items:
            raise ValueError("Cannot confirm an order with no items")
        for oi in order.items:
            product = db.get(Product, oi.product_id)
            qty = float(oi.quantity)
            if product.current_stock < qty:
                raise ValueError(
                    f"Insufficient stock for '{product.name}': "
                    f"available {product.current_stock}, requested {qty}"
                )
            product.current_stock = float(product.current_stock) - qty
            db.add(StockMovement(
                product_id=product.id,
                quantity=qty,
                type=MovementType.exit,
                order_id=order_id,
            ))

    order.status = next_status
    db.commit()
    return _build_response(_load_order(db, order_id))
