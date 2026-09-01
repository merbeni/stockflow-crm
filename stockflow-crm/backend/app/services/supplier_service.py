from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


def get_supplier(db: Session, supplier_id: int, organization_id: int) -> Supplier | None:
    return (
        db.query(Supplier)
        .filter(Supplier.id == supplier_id, Supplier.organization_id == organization_id)
        .first()
    )


def list_suppliers(db: Session, organization_id: int) -> list[Supplier]:
    return (
        db.query(Supplier)
        .filter(Supplier.organization_id == organization_id)
        .order_by(Supplier.name)
        .all()
    )


def create_supplier(db: Session, payload: SupplierCreate, organization_id: int) -> Supplier:
    supplier = Supplier(**payload.model_dump(), organization_id=organization_id)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(db: Session, supplier: Supplier, payload: SupplierUpdate) -> Supplier:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


def delete_supplier(db: Session, supplier: Supplier) -> None:
    db.delete(supplier)
    db.commit()
