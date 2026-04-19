from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.invoice import ConfidenceLevel, Invoice, InvoiceItem, InvoiceStatus
from app.models.product import Product
from app.models.product_supplier_mapping import ProductSupplierMapping
from app.models.stock_movement import MovementType, StockMovement
from app.models.supplier import Supplier
from app.schemas.invoice import InvoiceConfirmPayload, InvoiceProcessResponse, InvoiceItemProcessed
from app.services.invoice.gemini_service import process_invoice_file


# ── helpers ───────────────────────────────────────────────────────────────────

def _match_supplier(db: Session, name: str | None) -> Supplier | None:
    if not name:
        return None
    return (
        db.query(Supplier)
        .filter(Supplier.name.ilike(f"%{name}%"))
        .first()
    )


def _auto_match_product(
    db: Session, supplier_id: int | None, description: str
) -> ProductSupplierMapping | None:
    """Primary match: exact supplier SKU mapping saved from a previous invoice."""
    if not supplier_id:
        return None
    return (
        db.query(ProductSupplierMapping)
        .options(joinedload(ProductSupplierMapping.product))
        .filter(
            ProductSupplierMapping.supplier_id == supplier_id,
            ProductSupplierMapping.supplier_sku.ilike(description),
        )
        .first()
    )


def _fallback_match_product(db: Session, description: str) -> Product | None:
    """Fallback: match a product whose SKU or name contains the description, or vice-versa."""
    return (
        db.query(Product)
        .filter(
            or_(
                Product.sku.ilike(f"%{description}%"),
                Product.name.ilike(f"%{description}%"),
            )
        )
        .first()
    )


# ── process (upload + Gemini) ─────────────────────────────────────────────────

def process_invoice(
    db: Session, file_bytes: bytes, mime_type: str
) -> InvoiceProcessResponse:
    gemini_data = process_invoice_file(file_bytes, mime_type)

    supplier = _match_supplier(db, gemini_data.get("supplier"))

    raw_date = gemini_data.get("date")
    invoice_date: date | None = None
    if raw_date:
        try:
            invoice_date = date.fromisoformat(raw_date)
        except ValueError:
            invoice_date = None

    invoice = Invoice(
        supplier_id=supplier.id if supplier else None,
        date=invoice_date,
        gemini_raw=gemini_data,
        status=InvoiceStatus.pending,
    )
    db.add(invoice)
    db.flush()  # get invoice.id before committing

    # Build a full product_id → supplier_sku map for the detected supplier so the
    # frontend can auto-fill the Supplier SKU field for any product the user picks.
    supplier_product_skus: dict[int, str] = {}
    if invoice.supplier_id:
        all_mappings = (
            db.query(ProductSupplierMapping)
            .options(joinedload(ProductSupplierMapping.product))
            .filter(ProductSupplierMapping.supplier_id == invoice.supplier_id)
            .all()
        )
        # Exclude mappings where supplier_sku is just the product name (bad data guard).
        supplier_product_skus = {
            m.product_id: m.supplier_sku
            for m in all_mappings
            if m.supplier_sku.lower() != m.product.name.lower()
        }

    processed_items: list[InvoiceItemProcessed] = []
    for raw in gemini_data.get("items", []):
        try:
            confidence = ConfidenceLevel(raw.get("confidence", "low"))
        except ValueError:
            confidence = ConfidenceLevel.low

        item = InvoiceItem(
            invoice_id=invoice.id,
            description=raw.get("description", ""),
            quantity=float(raw.get("quantity", 0)),
            unit_price=float(raw.get("unit_price", 0)),
            confidence=confidence,
        )
        db.add(item)
        db.flush()

        mapping = _auto_match_product(db, invoice.supplier_id, item.description)
        if mapping:
            s_product_id   = mapping.product_id
            s_product_name = mapping.product.name
            s_supplier_sku = supplier_product_skus.get(mapping.product_id)
        else:
            # Fallback: match by product SKU or name (partial, case-insensitive).
            product = _fallback_match_product(db, item.description)
            s_product_id   = product.id   if product else None
            s_product_name = product.name if product else None
            # Re-use the supplier_product_skus map (already built above) to fill
            # in the supplier SKU if this product was previously mapped to the supplier.
            s_supplier_sku = supplier_product_skus.get(product.id) if product else None

        processed_items.append(
            InvoiceItemProcessed(
                id=item.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                confidence=item.confidence,
                suggested_product_id=s_product_id,
                suggested_product_name=s_product_name,
                suggested_supplier_sku=s_supplier_sku,
            )
        )

    db.commit()

    return InvoiceProcessResponse(
        invoice_id=invoice.id,
        supplier=gemini_data.get("supplier"),
        supplier_id=invoice.supplier_id,
        date=invoice_date,
        items=processed_items,
        supplier_product_skus=supplier_product_skus,
    )


# ── confirm ───────────────────────────────────────────────────────────────────

def confirm_invoice(
    db: Session, invoice_id: int, payload: InvoiceConfirmPayload
) -> tuple[Invoice, list[Product]]:
    invoice = db.query(Invoice).options(joinedload(Invoice.items)).filter(
        Invoice.id == invoice_id
    ).first()
    if not invoice:
        raise ValueError("Invoice not found")
    if invoice.status != InvoiceStatus.pending:
        raise ValueError(f"Invoice is already {invoice.status.value}")

    # Resolve supplier
    if payload.supplier_id is not None:
        supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier {payload.supplier_id} not found")
        invoice.supplier_id = supplier.id
    elif payload.new_supplier is not None:
        ns = payload.new_supplier
        new_supplier = Supplier(
            name=ns.name,
            contact_name=ns.contact_name,
            email=str(ns.email),
            phone=ns.phone,
        )
        db.add(new_supplier)
        db.flush()
        invoice.supplier_id = new_supplier.id

    items_by_id = {item.id: item for item in invoice.items}
    touched_product_ids: list[int] = []

    for confirm_item in payload.items:
        inv_item = items_by_id.get(confirm_item.invoice_item_id)
        if not inv_item:
            if not confirm_item.skip:
                raise ValueError(f"Invoice item {confirm_item.invoice_item_id} not found")
            continue

        if confirm_item.skip:
            inv_item.skipped = True
            continue

        if confirm_item.product_id is None and confirm_item.new_product is None:
            raise ValueError(
                f"Item {confirm_item.invoice_item_id}: provide product_id or new_product"
            )

        # Resolve or create the product.
        if confirm_item.product_id is not None:
            product = db.query(Product).filter(
                Product.id == confirm_item.product_id
            ).first()
            if not product:
                raise ValueError(f"Product {confirm_item.product_id} not found")
        else:
            nd = confirm_item.new_product
            existing = db.query(Product).filter(Product.sku == nd.sku).first()
            if existing:
                raise ValueError(f"SKU '{nd.sku}' already exists")
            product = Product(
                sku=nd.sku,
                name=nd.name,
                description=nd.description,
                price=float(nd.price),
                current_stock=0.0,
                minimum_stock=float(nd.minimum_stock),
            )
            db.add(product)
            db.flush()

        # Update stock.
        product.current_stock = float(product.current_stock) + float(inv_item.quantity)
        touched_product_ids.append(product.id)

        # Create stock movement.
        db.add(StockMovement(
            product_id=product.id,
            quantity=float(inv_item.quantity),
            type=MovementType.entry,
            invoice_id=invoice.id,
        ))

        # Save supplier → SKU mapping only when user explicitly provided a SKU.
        explicit_sku = confirm_item.supplier_sku
        if invoice.supplier_id and explicit_sku:
            exists = db.query(ProductSupplierMapping).filter(
                ProductSupplierMapping.supplier_id == invoice.supplier_id,
                ProductSupplierMapping.supplier_sku == explicit_sku,
            ).first()
            if not exists:
                db.add(ProductSupplierMapping(
                    product_id=product.id,
                    supplier_id=invoice.supplier_id,
                    supplier_sku=explicit_sku,
                ))

        # Store for audit purposes (falls back to description if no SKU given).
        inv_item.supplier_sku = explicit_sku or inv_item.description

    invoice.status = InvoiceStatus.confirmed
    db.commit()
    db.refresh(invoice)

    low_stock: list[Product] = []
    if touched_product_ids:
        low_stock = (
            db.query(Product)
            .filter(
                Product.id.in_(touched_product_ids),
                Product.current_stock < Product.minimum_stock,
            )
            .all()
        )

    return invoice, low_stock


# ── reject ────────────────────────────────────────────────────────────────────

def reject_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise ValueError("Invoice not found")
    if invoice.status != InvoiceStatus.pending:
        raise ValueError(f"Invoice is already {invoice.status.value}")
    invoice.status = InvoiceStatus.rejected
    db.commit()
    db.refresh(invoice)
    return invoice


# ── list / get ────────────────────────────────────────────────────────────────

def list_invoices(db: Session) -> list[Invoice]:
    return (
        db.query(Invoice)
        .options(joinedload(Invoice.supplier), joinedload(Invoice.items))
        .order_by(Invoice.created_at.desc())
        .all()
    )


def get_invoice(db: Session, invoice_id: int) -> Invoice | None:
    return (
        db.query(Invoice)
        .options(joinedload(Invoice.supplier), joinedload(Invoice.items))
        .filter(Invoice.id == invoice_id)
        .first()
    )
