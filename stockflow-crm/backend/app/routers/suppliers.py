from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate
from app.services.supplier_service import (
    create_supplier,
    delete_supplier,
    get_supplier,
    list_suppliers,
    update_supplier,
)

router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[SupplierResponse])
def get_suppliers(db: Session = Depends(get_db)):
    return list_suppliers(db)


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create(payload: SupplierCreate, db: Session = Depends(get_db)):
    return create_supplier(db, payload)


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_one(supplier_id: int, db: Session = Depends(get_db)):
    supplier = get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update(supplier_id: int, payload: SupplierUpdate, db: Session = Depends(get_db)):
    supplier = get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return update_supplier(db, supplier, payload)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(supplier_id: int, db: Session = Depends(get_db)):
    supplier = get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    delete_supplier(db, supplier)
