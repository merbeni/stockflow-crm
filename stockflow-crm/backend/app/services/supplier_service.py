from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models.invoice import Invoice
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


def deletability_map(
    db: Session, suppliers: list[Supplier]
) -> dict[int, tuple[bool, str | None]]:
    """
    Calcula en bloque si cada proveedor puede eliminarse y, si no, por qué.

    Igual que en clientes: sin esto el borrado fallaba recién en la base y el
    usuario recibía el mensaje genérico de integridad referencial, que no dice
    qué depende del proveedor ni qué hacer al respecto.
    """
    if not suppliers:
        return {}
    conteo = dict(
        db.query(Invoice.supplier_id, func.count(Invoice.id))
        .filter(Invoice.supplier_id.in_([s.id for s in suppliers]))
        .group_by(Invoice.supplier_id)
        .all()
    )
    resultado: dict[int, tuple[bool, str | None]] = {}
    for supplier in suppliers:
        facturas = conteo.get(supplier.id, 0)
        motivo = (
            f"El proveedor tiene {facturas} factura(s) cargadas. Para conservar "
            "la trazabilidad del stock no se puede eliminar."
            if facturas
            else None
        )
        resultado[supplier.id] = (motivo is None, motivo)
    return resultado


def delete_supplier(db: Session, supplier: Supplier) -> None:
    puede, motivo = deletability_map(db, [supplier])[supplier.id]
    if not puede:
        raise DomainError(motivo, status_code=409)

    db.delete(supplier)
    db.commit()
