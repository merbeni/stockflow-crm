"""
Genera el Diagrama de Flujo de StockFlow CRM en PDF (blanco y negro, 3 páginas).
Ejecutar: python generate_flowchart.py
"""
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4

W, H = A4   # 595.28 x 841.89
CX = W / 2  # 297.64

PROC_W  = 185
PROC_H  = 34
TERM_W  = 160
TERM_H  = 26
DEC_HW  = 65   # diamond half-width
DEC_HH  = 28   # diamond half-height


# ── color helpers ──────────────────────────────────────────────────────────────
def _w(c): c.setFillColorRGB(1, 1, 1)
def _b(c): c.setFillColorRGB(0, 0, 0)


# ── shapes ─────────────────────────────────────────────────────────────────────
def draw_terminal(c, cx, cy, text, w=TERM_W, h=TERM_H):
    _w(c)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.5)
    c.roundRect(cx - w/2, cy - h/2, w, h, h/2, stroke=1, fill=1)
    c.setLineWidth(1)
    _b(c)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, cy - 3, text)


def draw_process(c, cx, cy, text, w=PROC_W, h=PROC_H):
    _w(c)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(cx - w/2, cy - h/2, w, h, stroke=1, fill=1)
    _b(c)
    c.setFont("Helvetica", 8)
    lines = text.split('\n')
    lh = 10
    sy = cy + (len(lines) - 1) * lh / 2 - 3
    for i, ln in enumerate(lines):
        c.drawCentredString(cx, sy - i * lh, ln)


def draw_decision(c, cx, cy, text, hw=DEC_HW, hh=DEC_HH):
    _w(c)
    c.setStrokeColorRGB(0, 0, 0)
    p = c.beginPath()
    p.moveTo(cx, cy + hh); p.lineTo(cx + hw, cy)
    p.lineTo(cx, cy - hh); p.lineTo(cx - hw, cy)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    _b(c)
    c.setFont("Helvetica", 7.5)
    lines = text.split('\n')
    lh = 9.5
    sy = cy + (len(lines) - 1) * lh / 2 - 3
    for i, ln in enumerate(lines):
        c.drawCentredString(cx, sy - i * lh, ln)


# ── arrows ─────────────────────────────────────────────────────────────────────
def _ah(c, x, y, d="down"):
    s = 5
    _b(c)
    p = c.beginPath()
    if d == "down":
        p.moveTo(x, y); p.lineTo(x-s, y+s*1.6); p.lineTo(x+s, y+s*1.6)
    elif d == "up":
        p.moveTo(x, y); p.lineTo(x-s, y-s*1.6); p.lineTo(x+s, y-s*1.6)
    elif d == "right":
        p.moveTo(x, y); p.lineTo(x-s*1.6, y+s); p.lineTo(x-s*1.6, y-s)
    elif d == "left":
        p.moveTo(x, y); p.lineTo(x+s*1.6, y+s); p.lineTo(x+s*1.6, y-s)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def varrow(c, x, yf, yt, lbl="", lx=8):
    c.setStrokeColorRGB(0, 0, 0)
    c.line(x, yf, x, yt + 9)
    _ah(c, x, yt, "down")
    if lbl:
        _b(c); c.setFont("Helvetica", 7)
        c.drawString(x + lx, (yf + yt) / 2 - 3, lbl)


def harrow(c, xf, y, xt, lbl="", ly=6):
    c.setStrokeColorRGB(0, 0, 0)
    if xt > xf:
        c.line(xf, y, xt - 9, y); _ah(c, xt, y, "right")
    else:
        c.line(xf, y, xt + 9, y); _ah(c, xt, y, "left")
    if lbl:
        _b(c); c.setFont("Helvetica", 7)
        c.drawCentredString((xf + xt) / 2, y + ly, lbl)


# ── page helpers ───────────────────────────────────────────────────────────────
def page_title(c, t, sub=""):
    _b(c)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(CX, H - 35, t)
    if sub:
        c.setFont("Helvetica", 8.5)
        c.drawCentredString(CX, H - 52, sub)


def legend(c):
    y, x = 28, 60
    _b(c); c.setFont("Helvetica-Bold", 8)
    c.drawString(30, 48, "Simbología:")
    for shp, lbl in [("oval", "Inicio / Fin"), ("rect", "Proceso"), ("diam", "Decisión")]:
        _w(c)
        if shp == "oval":
            c.roundRect(x - 22, y - 7, 44, 14, 7, stroke=1, fill=1)
        elif shp == "rect":
            c.rect(x - 22, y - 7, 44, 14, stroke=1, fill=1)
        else:
            p = c.beginPath()
            p.moveTo(x, y+9); p.lineTo(x+18, y); p.lineTo(x, y-9); p.lineTo(x-18, y)
            p.close(); c.drawPath(p, stroke=1, fill=1)
        _b(c); c.setFont("Helvetica", 7.5)
        c.drawString(x + 26, y - 3, lbl)
        x += 130


# ── Flow 1: Autenticación ──────────────────────────────────────────────────────
def flow_auth(c):
    page_title(c, "Diagrama de Flujo 1 — Autenticación de Usuario",
               "Proceso de inicio de sesión con JWT (token válido 60 minutos)")

    cx  = CX
    ECX = 490   # error box center-x
    EW  = 155   # error box width

    Y = dict(inicio=790, inp=725, dec=655, tok=578, red=513, ses=448, fin=383)

    draw_terminal(c, cx, Y['inicio'], "INICIO")
    draw_process (c, cx, Y['inp'],   "Ingresar email y contraseña")
    draw_decision(c, cx, Y['dec'],   "¿Credenciales\nválidas?")
    draw_process (c, ECX, Y['dec'],  "Mostrar error de acceso", w=EW)
    draw_process (c, cx, Y['tok'],   "Generar token JWT")
    draw_process (c, cx, Y['red'],   "Redirigir al panel principal")
    draw_process (c, cx, Y['ses'],   "Sesión activa (expira en 60 min)")
    draw_terminal(c, cx, Y['fin'],   "FIN")

    # Main path
    varrow(c, cx, Y['inicio'] - 13,      Y['inp'] + 17)
    varrow(c, cx, Y['inp']    - 17,      Y['dec'] + DEC_HH)
    varrow(c, cx, Y['dec']    - DEC_HH,  Y['tok'] + 17, "Sí")
    varrow(c, cx, Y['tok']    - 17,      Y['red'] + 17)
    varrow(c, cx, Y['red']    - 17,      Y['ses'] + 17)
    varrow(c, cx, Y['ses']    - 17,      Y['fin'] + 13)

    # Decision "No" → error box
    harrow(c, cx + DEC_HW, Y['dec'], ECX - EW//2, "No")
    # Error box top → up to input row → left back into input box
    c.setStrokeColorRGB(0, 0, 0)
    c.line(ECX, Y['dec'] + 18, ECX, Y['inp'])
    harrow(c, ECX, Y['inp'], cx + PROC_W//2)

    legend(c)


# ── Flow 2: Procesamiento de Factura con IA ────────────────────────────────────
def flow_invoice(c):
    page_title(c, "Diagrama de Flujo 2 — Procesamiento de Factura con IA",
               "Proceso: carga de archivo → análisis Gemini 2.5 Flash → revisión → confirmación")

    cx  = CX
    RCX = 490   # right side boxes
    LCX = 105   # left side (reject)
    SW  = 155   # side box width

    Y = dict(inicio=800, upl=740, fmt=674, gem=606, gio=538,
             items=470, rev=405, dec=337, conf=267, ent=202, sav=137, fin=77)

    draw_terminal(c, cx, Y['inicio'], "INICIO")
    draw_process (c, cx, Y['upl'],  "Seleccionar archivo (PDF / JPG / PNG, máx. 20 MB)")
    draw_decision(c, cx, Y['fmt'],  "¿Formato y\ntamaño válido?")
    draw_process (c, RCX, Y['fmt'], "Error: formato no\nadmitido o archivo\ndemasiado grande", w=SW, h=46)
    draw_process (c, cx, Y['gem'],  "Enviar archivo a Gemini 2.5 Flash")
    draw_decision(c, cx, Y['gio'],  "¿Análisis\nexitoso?")
    draw_process (c, RCX, Y['gio'], "Servicio saturado\no no disponible\n(límite free trial)", w=SW, h=46)
    draw_process (c, cx, Y['items'],"Mostrar ítems detectados\ncon nivel de confianza (Alta / Media / Baja)")
    draw_process (c, cx, Y['rev'],  "Revisar, editar y asignar\nproductos a cada ítem")
    draw_decision(c, cx, Y['dec'],  "¿Confirmar\no Rechazar?")
    draw_process (c, LCX, Y['dec'], "Factura\nRECHAZADA", w=SW, h=40)
    draw_process (c, cx, Y['conf'], "Actualizar stock por cada ítem confirmado")
    draw_process (c, cx, Y['ent'],  "Registrar movimientos de tipo Entrada")
    draw_process (c, cx, Y['sav'],  "Guardar mapeo SKU proveedor — Estado: CONFIRMADA")
    draw_terminal(c, cx, Y['fin'],  "FIN")

    # Main path
    varrow(c, cx, Y['inicio'] - 13,     Y['upl']   + 17)
    varrow(c, cx, Y['upl']    - 17,     Y['fmt']   + DEC_HH)
    varrow(c, cx, Y['fmt']    - DEC_HH, Y['gem']   + 17,     "Sí")
    varrow(c, cx, Y['gem']    - 17,     Y['gio']   + DEC_HH)
    varrow(c, cx, Y['gio']    - DEC_HH, Y['items'] + 17,     "Sí")
    varrow(c, cx, Y['items']  - 17,     Y['rev']   + 17)
    varrow(c, cx, Y['rev']    - 17,     Y['dec']   + DEC_HH)
    varrow(c, cx, Y['dec']    - DEC_HH, Y['conf']  + 17,     "Confirmar")
    varrow(c, cx, Y['conf']   - 17,     Y['ent']   + 17)
    varrow(c, cx, Y['ent']    - 17,     Y['sav']   + 17)
    varrow(c, cx, Y['sav']    - 17,     Y['fin']   + 13)

    # Format error → dead end (right)
    harrow(c, cx + DEC_HW, Y['fmt'], RCX - SW//2, "No")

    # Gemini API error → retry loop (right → up → left back to gemini)
    harrow(c, cx + DEC_HW, Y['gio'], RCX - SW//2, "No")
    c.setStrokeColorRGB(0, 0, 0)
    c.line(RCX, Y['gio'] + 24, RCX, Y['gem'] + 5)
    harrow(c, RCX, Y['gem'] + 5, cx + PROC_W//2, "Reintentar")

    # Reject path (left)
    harrow(c, cx - DEC_HW, Y['dec'], LCX + SW//2, "Rechazar")

    legend(c)


# ── Flow 3: Gestión de Pedidos ─────────────────────────────────────────────────
def flow_orders(c):
    page_title(c, "Diagrama de Flujo 3 — Gestión de Pedidos",
               "Proceso: creación, adición de ítems y ciclo de estados (Pendiente → Entregado)")

    cx  = CX
    RCX = 490
    SW  = 155

    Y = dict(inicio=800, cre=737, add=670, stk=602, itm=533,
             adv1=464, pst=396, ded=328, em1=262, adv2=198, em2=134, fin=74)

    draw_terminal(c, cx, Y['inicio'], "INICIO")
    draw_process (c, cx, Y['cre'],  "Crear pedido — Estado: Pendiente")
    draw_process (c, cx, Y['add'],  "Agregar ítems al pedido")
    draw_decision(c, cx, Y['stk'],  "¿Stock del\nproducto\nsuficiente?")
    draw_process (c, RCX, Y['stk'], "Error: stock\ninsuficiente al\nagregar ítem", w=SW, h=46)
    draw_process (c, cx, Y['itm'],  "Ítem agregado — Total actualizado")
    draw_process (c, cx, Y['adv1'], "Avanzar pedido: Pendiente → Procesando")
    draw_decision(c, cx, Y['pst'],  "¿Stock aún\nsuficiente?")
    draw_process (c, RCX, Y['pst'], "Error: sin stock\nPedido permanece\nPendiente", w=SW, h=46)
    draw_process (c, cx, Y['ded'],  "Descontar stock — Registrar movimiento Venta")
    draw_process (c, cx, Y['em1'],  "Notificar cliente por email — Estado: Enviado")
    draw_process (c, cx, Y['adv2'], "Avanzar: Enviado → Entregado")
    draw_process (c, cx, Y['em2'],  "Notificar cliente por email — Estado: Entregado")
    draw_terminal(c, cx, Y['fin'],  "FIN")

    # Main path
    varrow(c, cx, Y['inicio'] - 13,     Y['cre']  + 17)
    varrow(c, cx, Y['cre']    - 17,     Y['add']  + 17)
    varrow(c, cx, Y['add']    - 17,     Y['stk']  + DEC_HH)
    varrow(c, cx, Y['stk']    - DEC_HH, Y['itm']  + 17,     "Sí")
    varrow(c, cx, Y['itm']    - 17,     Y['adv1'] + 17)
    varrow(c, cx, Y['adv1']   - 17,     Y['pst']  + DEC_HH)
    varrow(c, cx, Y['pst']    - DEC_HH, Y['ded']  + 17,     "Sí")
    varrow(c, cx, Y['ded']    - 17,     Y['em1']  + 17)
    varrow(c, cx, Y['em1']    - 17,     Y['adv2'] + 17)
    varrow(c, cx, Y['adv2']   - 17,     Y['em2']  + 17)
    varrow(c, cx, Y['em2']    - 17,     Y['fin']  + 13)

    # Stock error at add-item → loop back
    harrow(c, cx + DEC_HW, Y['stk'], RCX - SW//2, "No")
    c.setStrokeColorRGB(0, 0, 0)
    c.line(RCX, Y['stk'] + 24, RCX, Y['add'] + 5)
    harrow(c, RCX, Y['add'] + 5, cx + PROC_W//2, "Corregir")

    # Stock error at advance → dead end (right)
    harrow(c, cx + DEC_HW, Y['pst'], RCX - SW//2, "No")

    legend(c)


# ── Main ───────────────────────────────────────────────────────────────────────
def build():
    output = "Diagrama_de_Flujo_StockFlow.pdf"
    c = pdfcanvas.Canvas(output, pagesize=A4)
    c.setTitle("StockFlow CRM — Diagramas de Flujo")
    c.setAuthor("StockFlow CRM — Proyecto Final de Grado")

    flow_auth(c);    c.showPage()
    flow_invoice(c); c.showPage()
    flow_orders(c);  c.showPage()

    c.save()
    print(f"PDF generado: {output}")


if __name__ == "__main__":
    build()
