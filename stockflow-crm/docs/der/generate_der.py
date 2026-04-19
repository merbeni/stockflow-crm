"""
Genera el Diagrama Entidad-Relación (DER) normalizado de StockFlow CRM en PDF.
Blanco y negro, A4 landscape.
Ejecutar: python generate_der.py
"""
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import landscape, A4

W, H = landscape(A4)   # 841.89 x 595.28

BOX_W    = 135
HALF_W   = BOX_W / 2
HDR_H    = 15
FIELD_H  = 12


# ── entity drawing ─────────────────────────────────────────────────────────────
def draw_entity(c, cx, y_top, name, fields):
    """
    Draw one entity box.
    fields: list of (name, type_str, is_pk, is_fk)
    Returns geometry dict used for connection-point calculations.
    """
    h = HDR_H + len(fields) * FIELD_H
    xl = cx - HALF_W
    xr = cx + HALF_W
    yb = y_top - h
    yc = y_top - h / 2

    # Header — dark fill, white text
    c.setFillColorRGB(0.18, 0.18, 0.18)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(xl, y_top - HDR_H, BOX_W, HDR_H, stroke=1, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(cx, y_top - HDR_H + 3.5, name)

    # Fields
    for i, (fname, ftype, is_pk, is_fk) in enumerate(fields):
        yf = y_top - HDR_H - (i + 1) * FIELD_H
        if i % 2 == 0:
            c.setFillColorRGB(0.93, 0.93, 0.93)
        else:
            c.setFillColorRGB(1, 1, 1)
        c.setStrokeColorRGB(0, 0, 0)
        c.rect(xl, yf, BOX_W, FIELD_H, stroke=1, fill=1)

        c.setFillColorRGB(0, 0, 0)
        if is_pk:
            prefix = "PK "
            c.setFont("Helvetica-Bold", 7)
        elif is_fk:
            prefix = "FK "
            c.setFont("Helvetica-Oblique", 7)
        else:
            prefix = "   "
            c.setFont("Helvetica", 7)

        label = f"{prefix}{fname}"
        c.drawString(xl + 3, yf + 3, label)
        c.setFont("Helvetica", 6.5)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawRightString(xr - 3, yf + 3, ftype)

    return dict(cx=cx, y_top=y_top, y_bottom=yb, y_center=yc,
                x_left=xl, x_right=xr, name=name)


# ── relationship lines ─────────────────────────────────────────────────────────
def _edge(box, tcx, tcy):
    """Return the border point of box nearest to target (tcx, tcy)."""
    dx = tcx - box['cx']
    dy = tcy - box['y_center']
    if abs(dx) > abs(dy) * 0.9:
        return (box['x_right'], box['y_center']) if dx > 0 else (box['x_left'], box['y_center'])
    else:
        return (box['cx'], box['y_top']) if dy > 0 else (box['cx'], box['y_bottom'])


def draw_rel(c, b1, b2, c1="N", c2="1"):
    """Draw a relationship line between two entity boxes."""
    p1 = _edge(b1, b2['cx'], b2['y_center'])
    p2 = _edge(b2, b1['cx'], b1['y_center'])

    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.6)
    c.line(p1[0], p1[1], p2[0], p2[1])
    c.setLineWidth(1)

    # Cardinality labels
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = (dx**2 + dy**2) ** 0.5
    if length < 1:
        return
    nx, ny = dx / length, dy / length
    off = 13

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(p1[0] + nx * off - 4, p1[1] + ny * off - 3, c1)
    c.drawString(p2[0] - nx * off - 4, p2[1] - ny * off - 3, c2)


# ── main diagram ───────────────────────────────────────────────────────────────
def build():
    output = "DER_StockFlow.pdf"
    c = pdfcanvas.Canvas(output, pagesize=landscape(A4))
    c.setTitle("StockFlow CRM — DER Normalizado")
    c.setAuthor("StockFlow CRM — Proyecto Final de Grado")

    # Title
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(W / 2, H - 24, "StockFlow CRM — Diagrama Entidad-Relación (DER)")
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, H - 38, "Base de datos PostgreSQL 16 — Esquema normalizado")

    # ── Entity definitions ─────────────────────────────────────────────────────
    #   (field_name, type_str, is_pk, is_fk)
    ENTITIES = {
        'users': {
            'cx': 100, 'y_top': 530,
            'fields': [
                ('id',              'INT',          True,  False),
                ('email',           'VARCHAR(255)', False, False),
                ('hashed_password', 'VARCHAR(255)', False, False),
                ('role',            'ENUM',         False, False),
                ('created_at',      'TIMESTAMPTZ',  False, False),
            ]
        },
        'products': {
            'cx': 400, 'y_top': 535,
            'fields': [
                ('id',            'INT',           True,  False),
                ('sku',           'VARCHAR(100)',  False, False),
                ('name',          'VARCHAR(255)',  False, False),
                ('description',   'TEXT',          False, False),
                ('price',         'NUMERIC(10,2)', False, False),
                ('current_stock', 'NUMERIC(10,3)', False, False),
                ('minimum_stock', 'NUMERIC(10,3)', False, False),
                ('is_active',     'BOOLEAN',       False, False),
                ('created_at',    'TIMESTAMPTZ',   False, False),
            ]
        },
        'suppliers': {
            'cx': 730, 'y_top': 530,
            'fields': [
                ('id',           'INT',          True,  False),
                ('name',         'VARCHAR(255)', False, False),
                ('contact_name', 'VARCHAR(255)', False, False),
                ('email',        'VARCHAR(255)', False, False),
                ('phone',        'VARCHAR(50)',  False, False),
                ('created_at',   'TIMESTAMPTZ',  False, False),
            ]
        },
        'invoices': {
            'cx': 200, 'y_top': 345,
            'fields': [
                ('id',          'INT',          True,  False),
                ('supplier_id', 'INT',          False, True),
                ('date',        'DATE',         False, False),
                ('file_url',    'VARCHAR(500)', False, False),
                ('gemini_raw',  'JSONB',        False, False),
                ('status',      'ENUM',         False, False),
                ('created_at',  'TIMESTAMPTZ',  False, False),
            ]
        },
        'stock_movements': {
            'cx': 400, 'y_top': 345,
            'fields': [
                ('id',         'INT',           True,  False),
                ('product_id', 'INT',           False, True),
                ('quantity',   'NUMERIC(10,3)', False, False),
                ('type',       'ENUM',          False, False),
                ('invoice_id', 'INT',           False, True),
                ('order_id',   'INT',           False, True),
                ('created_at', 'TIMESTAMPTZ',   False, False),
            ]
        },
        'orders': {
            'cx': 600, 'y_top': 345,
            'fields': [
                ('id',          'INT',         True,  False),
                ('customer_id', 'INT',         False, True),
                ('status',      'ENUM',        False, False),
                ('created_at',  'TIMESTAMPTZ', False, False),
            ]
        },
        'invoice_items': {
            'cx': 100, 'y_top': 145,
            'fields': [
                ('id',           'INT',          True,  False),
                ('invoice_id',   'INT',          False, True),
                ('description',  'VARCHAR(500)', False, False),
                ('quantity',     'NUMERIC(10,3)',False, False),
                ('unit_price',   'NUMERIC(10,2)',False, False),
                ('confidence',   'ENUM',         False, False),
                ('supplier_sku', 'VARCHAR(100)', False, False),
                ('skipped',      'BOOLEAN',      False, False),
            ]
        },
        'product_supplier_mappings': {
            'cx': 285, 'y_top': 145,
            'fields': [
                ('id',           'INT',         True,  False),
                ('product_id',   'INT',         False, True),
                ('supplier_id',  'INT',         False, True),
                ('supplier_sku', 'VARCHAR(100)',False, False),
            ]
        },
        'order_items': {
            'cx': 575, 'y_top': 145,
            'fields': [
                ('id',         'INT',           True,  False),
                ('order_id',   'INT',           False, True),
                ('product_id', 'INT',           False, True),
                ('quantity',   'NUMERIC(10,3)', False, False),
                ('unit_price', 'NUMERIC(10,2)', False, False),
            ]
        },
        'customers': {
            'cx': 740, 'y_top': 145,
            'fields': [
                ('id',         'INT',          True,  False),
                ('name',       'VARCHAR(255)', False, False),
                ('email',      'VARCHAR(255)', False, False),
                ('phone',      'VARCHAR(50)',  False, False),
                ('address',    'TEXT',         False, False),
                ('created_at', 'TIMESTAMPTZ',  False, False),
            ]
        },
    }

    # Draw relationship lines FIRST (so entity boxes render on top)
    boxes = {}
    for name, data in ENTITIES.items():
        h = HDR_H + len(data['fields']) * FIELD_H
        xl = data['cx'] - HALF_W
        xr = data['cx'] + HALF_W
        yb = data['y_top'] - h
        yc = data['y_top'] - h / 2
        boxes[name] = dict(cx=data['cx'], y_top=data['y_top'], y_bottom=yb,
                           y_center=yc, x_left=xl, x_right=xr, name=name)

    RELATIONS = [
        # (entity_with_FK,               referenced_entity,  card_fk_side, card_ref_side)
        ('invoices',                    'suppliers',         'N', '1'),
        ('invoice_items',               'invoices',          'N', '1'),
        ('stock_movements',             'products',          'N', '1'),
        ('stock_movements',             'invoices',          'N', '1'),
        ('stock_movements',             'orders',            'N', '1'),
        ('orders',                      'customers',         'N', '1'),
        ('order_items',                 'orders',            'N', '1'),
        ('order_items',                 'products',          'N', '1'),
        ('product_supplier_mappings',   'products',          'N', '1'),
        ('product_supplier_mappings',   'suppliers',         'N', '1'),
    ]
    for e1, e2, c1, c2 in RELATIONS:
        draw_rel(c, boxes[e1], boxes[e2], c1, c2)

    # Draw entities on top of lines
    for name, data in ENTITIES.items():
        boxes[name] = draw_entity(c, data['cx'], data['y_top'], name, data['fields'])

    # Legend
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(28, 20,
        "PK = Clave primaria   |   FK = Clave foránea   |   N:1 = Muchos a uno   |   "
        "ENUM = Enumeración PostgreSQL   |   JSONB = JSON binario")

    c.save()
    print(f"PDF generado: {output}")


if __name__ == "__main__":
    build()
