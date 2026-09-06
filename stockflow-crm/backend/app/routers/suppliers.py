from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_org_id, get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate
from app.services.supplier_service import (
    create_supplier,
    deletability_map,
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


def _a_respuesta(db: Session, registro: Supplier) -> SupplierResponse:
    puede, motivo = deletability_map(db, [registro])[registro.id]
    respuesta = SupplierResponse.model_validate(registro)
    respuesta.can_delete = puede
    respuesta.delete_blocked_reason = motivo
    return respuesta


def _a_respuestas(db: Session, registros: list[Supplier]) -> list[SupplierResponse]:
    borrables = deletability_map(db, registros)
    respuestas = []
    for registro in registros:
        puede, motivo = borrables[registro.id]
        respuesta = SupplierResponse.model_validate(registro)
        respuesta.can_delete = puede
        respuesta.delete_blocked_reason = motivo
        respuestas.append(respuesta)
    return respuestas


def _get_or_404(db: Session, supplier_id: int, org_id: int) -> Supplier:
    supplier = get_supplier(db, supplier_id, org_id)
    if not supplier:
        raise NotFoundError("No encontramos ese proveedor.")
    return supplier


@router.get("", response_model=list[SupplierResponse])
def get_suppliers(
    org_id: int = Depends(get_current_org_id), db: Session = Depends(get_db)
):
    return _a_respuestas(db, list_suppliers(db, org_id))


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: SupplierCreate,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return _a_respuesta(db, create_supplier(db, payload, org_id))


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_one(
    supplier_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return _a_respuesta(db, _get_or_404(db, supplier_id, org_id))


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update(
    supplier_id: int,
    payload: SupplierUpdate,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    supplier = _get_or_404(db, supplier_id, org_id)
    return _a_respuesta(db, update_supplier(db, supplier, payload))


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    supplier_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    delete_supplier(db, _get_or_404(db, supplier_id, org_id))
