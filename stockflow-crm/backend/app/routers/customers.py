from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
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


@router.get("", response_model=list[CustomerResponse])
def get_all(db: Session = Depends(get_db)):
    return list_customers(db)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create(payload: CustomerCreate, db: Session = Depends(get_db)):
    return create_customer(db, payload)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_one(customer_id: int, db: Session = Depends(get_db)):
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return update_customer(db, customer, payload)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(customer_id: int, db: Session = Depends(get_db)):
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    delete_customer(db, customer)


@router.get("/{customer_id}/orders", response_model=CustomerOrderHistory)
def get_orders(customer_id: int, db: Session = Depends(get_db)):
    history = get_order_history(db, customer_id)
    if not history:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return history
