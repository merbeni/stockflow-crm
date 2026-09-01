from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_org_id, get_current_user
from app.core.errors import DomainError, NotFoundError
from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import (
    create_product,
    delete_product,
    deletability_map,
    get_product,
    get_product_by_sku,
    list_products,
    update_product,
)

router = APIRouter(
    prefix="/products",
    tags=["inventory"],
    dependencies=[Depends(get_current_user)],
)


def _to_response(db: Session, product: Product) -> ProductResponse:
    puede, motivo = deletability_map(db, [product])[product.id]
    response = ProductResponse.model_validate(product)
    response.can_delete = puede
    response.delete_blocked_reason = motivo
    return response


def _to_responses(db: Session, products: list[Product]) -> list[ProductResponse]:
    borrables = deletability_map(db, products)
    respuestas = []
    for product in products:
        puede, motivo = borrables[product.id]
        response = ProductResponse.model_validate(product)
        response.can_delete = puede
        response.delete_blocked_reason = motivo
        respuestas.append(response)
    return respuestas


def _get_or_404(db: Session, product_id: int, org_id: int) -> Product:
    product = get_product(db, product_id, org_id)
    if not product:
        # 404 y no 403: confirmar la existencia de un producto de otra
        # organización ya sería filtrar información.
        raise NotFoundError("No encontramos ese producto.")
    return product


@router.get("", response_model=list[ProductResponse])
def get_products(
    low_stock_only: bool = Query(False, description="Return only products below minimum stock"),
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return _to_responses(db, list_products(db, org_id, low_stock_only=low_stock_only))


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: ProductCreate,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    if get_product_by_sku(db, payload.sku, org_id):
        raise DomainError(
            f"Ya existe un producto con el SKU «{payload.sku}» en tu organización.",
            field="sku",
        )
    return _to_response(db, create_product(db, payload, org_id))


@router.get("/low-stock", response_model=list[ProductResponse])
def low_stock(
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    """Atajo: devuelve los productos cuyo stock está por debajo del mínimo."""
    return _to_responses(db, list_products(db, org_id, low_stock_only=True))


@router.get("/{product_id}", response_model=ProductResponse)
def get_one(
    product_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    return _to_response(db, _get_or_404(db, product_id, org_id))


@router.put("/{product_id}", response_model=ProductResponse)
def update(
    product_id: int,
    payload: ProductUpdate,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    product = _get_or_404(db, product_id, org_id)
    if payload.sku and payload.sku != product.sku and get_product_by_sku(db, payload.sku, org_id):
        raise DomainError(
            f"Ya existe un producto con el SKU «{payload.sku}» en tu organización.",
            field="sku",
        )
    return _to_response(db, update_product(db, product, payload))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    product_id: int,
    org_id: int = Depends(get_current_org_id),
    db: Session = Depends(get_db),
):
    product = _get_or_404(db, product_id, org_id)
    # delete_product lanza un DomainError con el motivo exacto si no corresponde.
    delete_product(db, product)
