from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.schemas.product import ProductCreate, ProductUpdate


def get_product(db: Session, product_id: int) -> Product | None:
    return db.query(Product).filter(Product.id == product_id).first()


def get_product_by_sku(db: Session, sku: str) -> Product | None:
    return db.query(Product).filter(Product.sku == sku).first()


def list_products(db: Session, low_stock_only: bool = False) -> list[Product]:
    query = db.query(Product)
    if low_stock_only:
        query = query.filter(Product.current_stock < Product.minimum_stock)
    return query.order_by(Product.name).all()


def create_product(db: Session, payload: ProductCreate) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)
    db.flush()
    if float(product.current_stock) != 0:
        db.add(StockMovement(
            product_id=product.id,
            quantity=float(product.current_stock),
            type=MovementType.entry,
        ))
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    data = payload.model_dump(exclude_unset=True)

    new_stock = data.get("current_stock")
    if new_stock is not None:
        old_stock = float(product.current_stock)
        new_stock = float(new_stock)
        diff = new_stock - old_stock
        if diff != 0:
            # Store signed quantity so the UI can show +/- for adjustments
            db.add(StockMovement(
                product_id=product.id,
                quantity=diff,
                type=MovementType.adjustment,
            ))

    for field, value in data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    db.delete(product)
    db.commit()
