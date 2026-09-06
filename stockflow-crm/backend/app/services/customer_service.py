from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import DomainError
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.schemas.customer import (
    CustomerCreate,
    CustomerOrderHistory,
    CustomerResponse,
    CustomerUpdate,
    OrderHistoryEntry,
    OrderItemSummary,
)


def get_customer(db: Session, customer_id: int, organization_id: int) -> Customer | None:
    return (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.organization_id == organization_id)
        .first()
    )


def list_customers(db: Session, organization_id: int) -> list[Customer]:
    stmt = (
        select(Customer)
        .where(Customer.organization_id == organization_id)
        .order_by(Customer.name)
    )
    return list(db.scalars(stmt))


def create_customer(db: Session, payload: CustomerCreate, organization_id: int) -> Customer:
    customer = Customer(**payload.model_dump(), organization_id=organization_id)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_customer(db: Session, customer: Customer, payload: CustomerUpdate) -> Customer:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


def deletability_map(
    db: Session, customers: list[Customer]
) -> dict[int, tuple[bool, str | None]]:
    """
    Calcula en bloque si cada cliente puede eliminarse y, si no, por qué.

    Sin esta comprobación el borrado llegaba hasta la base y volvía como una
    violación de integridad: el usuario leía un mensaje genérico sobre
    "información relacionada" en lugar de enterarse de que el cliente tiene
    pedidos, que es la única razón real por la que no se puede borrar.
    """
    if not customers:
        return {}
    conteo = dict(
        db.query(Order.customer_id, func.count(Order.id))
        .filter(Order.customer_id.in_([c.id for c in customers]))
        .group_by(Order.customer_id)
        .all()
    )
    resultado: dict[int, tuple[bool, str | None]] = {}
    for customer in customers:
        pedidos = conteo.get(customer.id, 0)
        motivo = (
            f"El cliente tiene {pedidos} pedido(s) registrados. Para conservar "
            "el historial de ventas no se puede eliminar."
            if pedidos
            else None
        )
        resultado[customer.id] = (motivo is None, motivo)
    return resultado


def delete_customer(db: Session, customer: Customer) -> None:
    puede, motivo = deletability_map(db, [customer])[customer.id]
    if not puede:
        raise DomainError(motivo, status_code=409)

    db.delete(customer)
    db.commit()


def get_order_history(
    db: Session, customer_id: int, organization_id: int
) -> CustomerOrderHistory | None:
    customer = get_customer(db, customer_id, organization_id)
    if not customer:
        return None

    stmt = (
        select(Order)
        .where(Order.customer_id == customer_id)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product)
        )
        .order_by(Order.created_at.desc())
    )
    orders = list(db.scalars(stmt).unique())

    order_entries = []
    for order in orders:
        items = []
        total = Decimal("0")
        for oi in order.items:
            qty = Decimal(str(oi.quantity))
            price = Decimal(str(oi.unit_price))
            items.append(OrderItemSummary(
                product_id=oi.product_id,
                product_sku=oi.product.sku,
                product_name=oi.product.name,
                quantity=qty,
                unit_price=price,
            ))
            total += qty * price
        order_entries.append(OrderHistoryEntry(
            id=order.id,
            status=order.status,
            created_at=order.created_at,
            items=items,
            total=total,
        ))

    return CustomerOrderHistory(
        customer=CustomerResponse.model_validate(customer),
        orders=order_entries,
    )
