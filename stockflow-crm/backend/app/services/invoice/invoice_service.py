from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.errors import DomainError, NotFoundError
from app.models.invoice import ConfidenceLevel, Invoice, InvoiceItem, InvoiceStatus
from app.models.product import Product
from app.models.product_supplier_mapping import ProductSupplierMapping
from app.models.stock_movement import MovementType, StockMovement
from app.models.supplier import Supplier
from app.schemas.invoice import InvoiceConfirmPayload, InvoiceProcessResponse, InvoiceItemProcessed
from app.services.invoice.gemini_service import process_invoice_file
from app.services.stock_rules import validar_cantidad


# ── helpers ───────────────────────────────────────────────────────────────────

def _match_supplier(db: Session, name: str | None, organization_id: int) -> Supplier | None:
    if not name:
        return None
    return (
        db.query(Supplier)
        .filter(
            Supplier.organization_id == organization_id,
            Supplier.name.ilike(f"%{name}%"),
        )
        .first()
    )


def _auto_match_product(
    db: Session, supplier_id: int | None, description: str
) -> ProductSupplierMapping | None:
    """Coincidencia principal: SKU del proveedor guardado en una factura anterior."""
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


def _fallback_match_product(
    db: Session, description: str, organization_id: int
) -> Product | None:
    """Alternativa: un producto cuyo SKU o nombre contenga la descripción."""
    return (
        db.query(Product)
        .filter(
            Product.organization_id == organization_id,
            or_(
                Product.sku.ilike(f"%{description}%"),
                Product.name.ilike(f"%{description}%"),
            ),
        )
        .first()
    )


# ── process (upload + Gemini) ─────────────────────────────────────────────────

def mapa_skus_del_proveedor(db: Session, supplier_id: int | None) -> dict[int, str]:
    """
    product_id → SKU con el que ese proveedor identifica al producto.

    Sirve para completar solo el campo «SKU del proveedor» cuando se elige un
    producto. Se descartan los mapeos cuyo SKU es igual al nombre del producto:
    son datos viejos que no aportan nada.
    """
    if not supplier_id:
        return {}
    mapeos = (
        db.query(ProductSupplierMapping)
        .options(joinedload(ProductSupplierMapping.product))
        .filter(ProductSupplierMapping.supplier_id == supplier_id)
        .all()
    )
    return {
        m.product_id: m.supplier_sku
        for m in mapeos
        if m.supplier_sku.lower() != m.product.name.lower()
    }


def sugerencia_para_linea(
    db: Session,
    descripcion: str,
    supplier_id: int | None,
    organization_id: int,
    skus_del_proveedor: dict[int, str],
) -> tuple[int | None, str | None, str | None]:
    """
    Producto que probablemente corresponda a una línea leída de la factura.

    Primero busca un mapeo guardado de ese proveedor —lo que ya se decidió en
    facturas anteriores— y si no hay, prueba por SKU o nombre del producto.
    """
    mapping = _auto_match_product(db, supplier_id, descripcion)
    if mapping:
        return (
            mapping.product_id,
            mapping.product.name,
            skus_del_proveedor.get(mapping.product_id),
        )
    product = _fallback_match_product(db, descripcion, organization_id)
    if not product:
        return None, None, None
    return product.id, product.name, skus_del_proveedor.get(product.id)


def sugerencias_de_factura(
    db: Session, invoice: Invoice, organization_id: int
) -> tuple[dict[int, tuple[int | None, str | None, str | None]], dict[int, str]]:
    """
    Rehace las sugerencias de una factura pendiente, para retomar la revisión.

    El emparejado automático se calculaba al procesar y solo viajaba en esa
    respuesta: quien cerraba la revisión y volvía más tarde —algo que la propia
    pantalla ofrece hacer— se encontraba con todas las líneas en blanco y tenía
    que rehacer a mano lo que el sistema ya había resuelto.
    """
    skus = mapa_skus_del_proveedor(db, invoice.supplier_id)
    return (
        {
            item.id: sugerencia_para_linea(
                db, item.description, invoice.supplier_id, organization_id, skus
            )
            for item in invoice.items
        },
        skus,
    )


def process_invoice(
    db: Session, file_bytes: bytes, mime_type: str, organization_id: int
) -> InvoiceProcessResponse:
    gemini_data = process_invoice_file(file_bytes, mime_type)

    # Control de contenido ANTES de escribir nada en la base. Sin esto, subir
    # una foto cualquiera creaba una factura con ítems inventados por la IA.
    raw_items = gemini_data.get("items") or []
    if gemini_data.get("is_invoice") is False:
        tipo = (gemini_data.get("document_type") or "").strip()
        detalle = f" Parece ser: {tipo}." if tipo else ""
        raise DomainError(
            f"El archivo que subiste no parece una factura ni un remito.{detalle} "
            "Subí el comprobante del proveedor en PDF o como imagen legible.",
            status_code=422,
            field="file",
        )

    if not raw_items:
        raise DomainError(
            "No pudimos identificar ninguna línea de productos en el documento. "
            "Verificá que la imagen se vea nítida y completa, o cargá la factura "
            "en PDF.",
            status_code=422,
            field="file",
        )

    supplier = _match_supplier(db, gemini_data.get("supplier"), organization_id)

    raw_date = gemini_data.get("date")
    invoice_date: date | None = None
    if raw_date:
        try:
            invoice_date = date.fromisoformat(raw_date)
        except (ValueError, TypeError):
            invoice_date = None

    invoice = Invoice(
        organization_id=organization_id,
        supplier_id=supplier.id if supplier else None,
        date=invoice_date,
        gemini_raw=gemini_data,
        status=InvoiceStatus.pending,
    )
    db.add(invoice)
    db.flush()  # get invoice.id before committing

    supplier_product_skus = mapa_skus_del_proveedor(db, invoice.supplier_id)

    processed_items: list[InvoiceItemProcessed] = []
    for raw in raw_items:
        try:
            confidence = ConfidenceLevel(raw.get("confidence", "low"))
        except ValueError:
            confidence = ConfidenceLevel.low

        item = InvoiceItem(
            invoice_id=invoice.id,
            description=raw.get("description", ""),
            quantity=float(raw.get("quantity", 0) or 0),
            unit_price=float(raw.get("unit_price", 0) or 0),
            confidence=confidence,
        )
        db.add(item)
        db.flush()

        s_product_id, s_product_name, s_supplier_sku = sugerencia_para_linea(
            db, item.description, invoice.supplier_id, organization_id,
            supplier_product_skus,
        )

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

_ESTADOS_ES = {
    InvoiceStatus.pending: "pendiente",
    InvoiceStatus.confirmed: "confirmada",
    InvoiceStatus.rejected: "rechazada",
}


def _referencia(inv_item: InvoiceItem | None, confirm_item) -> str:
    """
    Texto con el que el usuario reconoce la línea en pantalla.

    Se usa la descripción del producto en lugar del identificador interno: el
    mensaje "Item 48: provide product_id" no le decía nada a quien lo leía y
    además dejaba a la vista la estructura de la base de datos.
    """
    if inv_item and inv_item.description:
        return f"«{inv_item.description}»"
    return "sin descripción"


def confirm_invoice(
    db: Session, invoice_id: int, payload: InvoiceConfirmPayload, organization_id: int
) -> tuple[Invoice, list[Product]]:
    invoice = (
        db.query(Invoice)
        .options(joinedload(Invoice.items))
        .filter(Invoice.id == invoice_id, Invoice.organization_id == organization_id)
        .first()
    )
    if not invoice:
        raise NotFoundError("No encontramos esa factura.")
    if invoice.status != InvoiceStatus.pending:
        raise DomainError(
            f"Esta factura ya está {_ESTADOS_ES[invoice.status]} y no se puede "
            "volver a confirmar."
        )

    # Resolver el proveedor
    if payload.supplier_id is not None:
        supplier = (
            db.query(Supplier)
            .filter(
                Supplier.id == payload.supplier_id,
                Supplier.organization_id == organization_id,
            )
            .first()
        )
        if not supplier:
            raise NotFoundError("No encontramos el proveedor seleccionado.")
        invoice.supplier_id = supplier.id
    elif payload.new_supplier is not None:
        ns = payload.new_supplier
        new_supplier = Supplier(
            organization_id=organization_id,
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
                raise DomainError(
                    "Una de las líneas ya no existe en esta factura. Volvé a "
                    "abrir la revisión para trabajar sobre los datos actuales."
                )
            continue

        if confirm_item.skip:
            inv_item.skipped = True
            continue

        # Correcciones manuales sobre lo que extrajo la IA.
        if confirm_item.description is not None:
            inv_item.description = confirm_item.description
        if confirm_item.quantity is not None:
            inv_item.quantity = float(confirm_item.quantity)
        if confirm_item.unit_price is not None:
            inv_item.unit_price = float(confirm_item.unit_price)

        if confirm_item.product_id is None and confirm_item.new_product is None:
            raise DomainError(
                f"La línea {_referencia(inv_item, confirm_item)} no tiene un "
                "producto asignado. Elegí un producto existente, creá uno nuevo "
                "u omití la línea."
            )

        # Resolver o crear el producto.
        if confirm_item.product_id is not None:
            product = (
                db.query(Product)
                .filter(
                    Product.id == confirm_item.product_id,
                    Product.organization_id == organization_id,
                )
                .first()
            )
            if not product:
                raise DomainError(
                    f"El producto elegido para la línea {_referencia(inv_item, confirm_item)} "
                    "ya no está disponible. Seleccioná otro."
                )
        else:
            nd = confirm_item.new_product
            existing = (
                db.query(Product)
                .filter(
                    Product.sku == nd.sku,
                    Product.organization_id == organization_id,
                )
                .first()
            )
            if existing:
                raise DomainError(
                    f"Ya existe un producto con el SKU «{nd.sku}» "
                    f"({existing.name}). Elegilo de la lista en lugar de crear uno nuevo."
                )
            product = Product(
                organization_id=organization_id,
                sku=nd.sku,
                name=nd.name,
                description=nd.description,
                price=float(nd.price),
                current_stock=0.0,
                minimum_stock=float(nd.minimum_stock),
                allow_decimal_stock=nd.allow_decimal_stock,
            )
            db.add(product)
            db.flush()

        # La cantidad de la factura tiene que respetar la unidad del producto.
        validar_cantidad(
            inv_item.quantity,
            permite_decimales=product.allow_decimal_stock,
            nombre_producto=product.name,
        )

        # Actualizar stock.
        product.current_stock = float(product.current_stock) + float(inv_item.quantity)
        touched_product_ids.append(product.id)

        # Registrar el movimiento de stock.
        db.add(StockMovement(
            organization_id=organization_id,
            product_id=product.id,
            quantity=float(inv_item.quantity),
            type=MovementType.entry,
            invoice_id=invoice.id,
        ))

        # El mapeo proveedor → SKU solo se guarda si el usuario lo indicó.
        explicit_sku = confirm_item.supplier_sku
        if invoice.supplier_id and explicit_sku:
            exists = db.query(ProductSupplierMapping).filter(
                ProductSupplierMapping.supplier_id == invoice.supplier_id,
                ProductSupplierMapping.supplier_sku == explicit_sku,
            ).first()
            if not exists:
                db.add(ProductSupplierMapping(
                    organization_id=organization_id,
                    product_id=product.id,
                    supplier_id=invoice.supplier_id,
                    supplier_sku=explicit_sku,
                ))

        # Se guarda para la auditoría (usa la descripción si no se indicó SKU).
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

def reject_invoice(db: Session, invoice_id: int, organization_id: int) -> Invoice:
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.organization_id == organization_id)
        .first()
    )
    if not invoice:
        raise NotFoundError("No encontramos esa factura.")
    if invoice.status != InvoiceStatus.pending:
        raise DomainError(
            f"Esta factura ya está {_ESTADOS_ES[invoice.status]} y no se puede rechazar."
        )
    invoice.status = InvoiceStatus.rejected
    db.commit()
    db.refresh(invoice)
    return invoice


# ── list / get ────────────────────────────────────────────────────────────────

def list_invoices(db: Session, organization_id: int) -> list[Invoice]:
    return (
        db.query(Invoice)
        .options(joinedload(Invoice.supplier), joinedload(Invoice.items))
        .filter(Invoice.organization_id == organization_id)
        .order_by(Invoice.created_at.desc())
        .all()
    )


def get_invoice(db: Session, invoice_id: int, organization_id: int) -> Invoice | None:
    return (
        db.query(Invoice)
        .options(joinedload(Invoice.supplier), joinedload(Invoice.items))
        .filter(Invoice.id == invoice_id, Invoice.organization_id == organization_id)
        .first()
    )
