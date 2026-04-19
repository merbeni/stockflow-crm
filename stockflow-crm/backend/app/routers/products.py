from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import (
    create_product,
    delete_product,
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


@router.get("", response_model=list[ProductResponse])
def get_products(
    low_stock_only: bool = Query(False, description="Return only products below minimum stock"),
    db: Session = Depends(get_db),
):
    return list_products(db, low_stock_only=low_stock_only)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create(payload: ProductCreate, db: Session = Depends(get_db)):
    if get_product_by_sku(db, payload.sku):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SKU '{payload.sku}' already exists",
        )
    return create_product(db, payload)


@router.get("/low-stock", response_model=list[ProductResponse])
def low_stock(db: Session = Depends(get_db)):
    """Shortcut endpoint — returns products whose current stock is below minimum."""
    return list_products(db, low_stock_only=True)


@router.get("/{product_id}", response_model=ProductResponse)
def get_one(product_id: int, db: Session = Depends(get_db)):
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if payload.sku and payload.sku != product.sku and get_product_by_sku(db, payload.sku):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SKU '{payload.sku}' already exists",
        )
    return update_product(db, product, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(product_id: int, db: Session = Depends(get_db)):
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    try:
        delete_product(db, product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This product cannot be deleted because it has stock movements or order history. Deactivate it instead.",
        )
