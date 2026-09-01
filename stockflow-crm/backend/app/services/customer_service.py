from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

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


def delete_customer(db: Session, customer: Customer) -> None:
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
