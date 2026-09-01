from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_org_id, get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.schemas.order import OrderCreate, OrderItemAdd, OrderResponse
from app.services.email_service import send_order_status_email
from app.services.order_service import (
    add_item,
    advance_status,
    create_order,
    delete_order,
    get_order,
    list_orders,
    remove_item,
)

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[OrderResponse])
def get_all(org_id: int = Depends(get_current_org_id), db: Session = Depends(get_db)):
    return list_orders(db, org_id)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: OrderCreate,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return create_order(db, payload, org_id)


@router.get("/{order_id}", response_model=OrderResponse)
def get_one(
    order_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    order = get_order(db, order_id, org_id)
    if not order:
        raise NotFoundError("No encontramos ese pedido.")
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    order_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    delete_order(db, order_id, org_id)


@router.post("/{order_id}/items", response_model=OrderResponse)
def add_order_item(
    order_id: int,
    payload: OrderItemAdd,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return add_item(db, order_id, payload, org_id)


@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse)
def remove_order_item(
    order_id: int,
    item_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return remove_item(db, order_id, item_id, org_id)


@router.post("/{order_id}/advance", response_model=OrderResponse)
def advance(
    order_id: int,
    background_tasks: BackgroundTasks,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    order = advance_status(db, order_id, org_id)

    # El correo se envía en segundo plano para no demorar la respuesta.
    if order.customer_email:
        background_tasks.add_task(
            send_order_status_email,
            customer_email=order.customer_email,
            customer_name=order.customer_name,
            order_id=order.id,
            new_status=order.status.value,
            items=order.items,
            total=order.total,
        )

    return order
