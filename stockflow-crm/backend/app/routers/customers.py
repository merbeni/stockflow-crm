from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_org_id, get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.customer import Customer
from app.schemas.customer import (
    CustomerCreate,
    CustomerOrderHistory,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customer_service import (
    create_customer,
    delete_customer,
    get_customer,
    get_order_history,
    list_customers,
    update_customer,
)

router = APIRouter(
    prefix="/customers",
    tags=["customers"],
    dependencies=[Depends(get_current_user)],
)


def _get_or_404(db: Session, customer_id: int, org_id: int) -> Customer:
    customer = get_customer(db, customer_id, org_id)
    if not customer:
        raise NotFoundError("No encontramos ese cliente.")
    return customer


@router.get("", response_model=list[CustomerResponse])
def get_all(org_id: int = Depends(get_current_org_id), db: Session = Depends(get_db)):
    return list_customers(db, org_id)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: CustomerCreate,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return create_customer(db, payload, org_id)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_one(
    customer_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return _get_or_404(db, customer_id, org_id)


@router.put("/{customer_id}", response_model=CustomerResponse)
def update(
    customer_id: int,
    payload: CustomerUpdate,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return update_customer(db, _get_or_404(db, customer_id, org_id), payload)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    customer_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    delete_customer(db, _get_or_404(db, customer_id, org_id))


@router.get("/{customer_id}/orders", response_model=CustomerOrderHistory)
def get_orders(
    customer_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    history = get_order_history(db, customer_id, org_id)
    if not history:
        raise NotFoundError("No encontramos ese cliente.")
    return history
