import base64
import logging
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment, Disposition, FileContent, FileName, FileType, Mail,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

_STATUS_COPY = {
    "processing": ("Your order is being processed", "We have received your order and our team is preparing it."),
    "shipped":    ("Your order has been shipped",   "Great news! Your order is on its way to you."),
    "delivered":  ("Your order has been delivered", "Your order has been delivered. We hope you enjoy it!"),
}

_GREEN  = colors.HexColor("#064E3B")
_LIGHT  = colors.HexColor("#ECFDF5")
_BORDER = colors.HexColor("#D1FAE5")


# ── PDF helper ────────────────────────────────────────────────────────────────

def _build_order_pdf(
    order_id: int,
    customer_name: str,
    new_status: str,
    items: list,
    total: Decimal,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    muted = ParagraphStyle("muted", parent=styles["Normal"], textColor=colors.HexColor("#4B7A68"), fontSize=10)

    story = [
        Paragraph("StockFlow CRM", ParagraphStyle("brand", parent=styles["Title"], textColor=_GREEN)),
        Spacer(1, 0.3 * cm),
        Paragraph(f"Order #{order_id}", styles["Heading2"]),
        Spacer(1, 0.15 * cm),
        Paragraph(f"Customer: {customer_name}", muted),
        Paragraph(f"Status: {new_status.capitalize()}", muted),
        Spacer(1, 0.6 * cm),
    ]

    # Table rows
    header = ["Product", "SKU", "Qty", "Unit price", "Subtotal"]
    rows = [header]
    for item in items:
        qty   = float(item.quantity)
        price = float(item.unit_price)
        rows.append([
            item.product_name,
            item.product_sku,
            f"{qty:g}",
            f"${price:.2f}",
            f"${qty * price:.2f}",
        ])
    rows.append(["", "", "", "Total", f"${float(total):.2f}"])

    col_widths = [7 * cm, 3 * cm, 2 * cm, 3 * cm, 3 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",   (0, 0), (-1, 0),  _GREEN),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        # Data rows — alternating light background
        *[("BACKGROUND", (0, i), (-1, i), _LIGHT) for i in range(1, len(rows) - 1) if i % 2 == 0],
        # Total row
        ("FONTNAME",     (3, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE",    (0, -1), (-1, -1), 1, _GREEN),
        ("TOPPADDING",   (0, -1), (-1, -1), 8),
        # General
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("PADDING",      (0, 0), (-1, -1), 6),
        ("ALIGN",        (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",    (0, 0), (-1, -2), 0.4, _BORDER),
    ]))

    story.append(table)
    doc.build(story)
    return buffer.getvalue()


# ── SendGrid helper ───────────────────────────────────────────────────────────

def _send(to_email: str, subject: str, html: str, pdf_bytes: bytes | None = None, pdf_name: str = "order.pdf") -> None:
    """Send via SendGrid. Skips silently if API key is not configured."""
    if not settings.SENDGRID_API_KEY:
        return
    try:
        message = Mail(
            from_email=settings.SMTP_FROM_EMAIL or "noreply@stockflow.app",
            to_emails=to_email,
            subject=subject,
            html_content=html,
        )
        if pdf_bytes:
            message.add_attachment(Attachment(
                file_content=FileContent(base64.b64encode(pdf_bytes).decode()),
                file_name=FileName(pdf_name),
                file_type=FileType("application/pdf"),
                disposition=Disposition("attachment"),
            ))
        SendGridAPIClient(settings.SENDGRID_API_KEY).send(message)
    except Exception:
        logger.exception("Failed to send email to %s (subject: %s)", to_email, subject)


# ── Public functions ──────────────────────────────────────────────────────────

def send_order_status_email(
    customer_email: str,
    customer_name: str,
    order_id: int,
    new_status: str,
    items: list,
    total: Decimal,
) -> None:
    subject_suffix, body_line = _STATUS_COPY.get(new_status, (f"Status updated to {new_status}", ""))
    subject = f"Order #{order_id} — {subject_suffix}"
    html = f"""
    <html><body style="font-family:sans-serif;color:#1C1917;max-width:560px;margin:auto;padding:24px">
      <h2 style="color:#064E3B">StockFlow CRM</h2>
      <p>Hi <strong>{customer_name}</strong>,</p>
      <p>{body_line}</p>
      <div style="background:#ECFDF5;border:1px solid #D1FAE5;border-radius:12px;padding:16px 20px;margin:20px 0">
        <p style="margin:0;font-size:14px;color:#4B7A68">Order number</p>
        <p style="margin:4px 0 0;font-size:22px;font-weight:700;color:#064E3B">#{order_id}</p>
        <p style="margin:8px 0 0;font-size:14px">Status: <strong>{new_status.capitalize()}</strong></p>
      </div>
      <p style="color:#6B9E8A;font-size:12px">Please find your order summary attached as a PDF.</p>
    </body></html>
    """
    pdf = _build_order_pdf(order_id, customer_name, new_status, items, total)
    _send(customer_email, subject, html, pdf_bytes=pdf, pdf_name=f"order_{order_id}.pdf")


def send_welcome_email(user_email: str) -> None:
    subject = "Welcome to StockFlow CRM"
    html = f"""
    <html><body style="font-family:sans-serif;color:#1C1917;max-width:560px;margin:auto;padding:24px">
      <h2 style="color:#064E3B">Welcome to StockFlow CRM</h2>
      <p>Your account has been created successfully.</p>
      <div style="background:#ECFDF5;border:1px solid #D1FAE5;border-radius:12px;padding:16px 20px;margin:20px 0">
        <p style="margin:0;font-size:14px;color:#4B7A68">Account email</p>
        <p style="margin:4px 0 0;font-size:16px;font-weight:600;color:#064E3B">{user_email}</p>
      </div>
      <p>You can now sign in and start managing your inventory, suppliers, and orders.</p>
      <p style="color:#6B9E8A;font-size:12px">If you did not register for this account, please contact your administrator.</p>
    </body></html>
    """
    _send(user_email, subject, html)


def send_low_stock_alert(to_email: str, product_name: str, product_sku: str, current_stock: float, minimum_stock: float) -> None:
    subject = f"Low stock alert — {product_name}"
    html = f"""
    <html><body style="font-family:sans-serif;color:#1C1917;max-width:560px;margin:auto;padding:24px">
      <h2 style="color:#064E3B">StockFlow CRM — Low Stock Alert</h2>
      <p>A product has dropped below its minimum stock level after the latest invoice confirmation.</p>
      <div style="background:#FEE2E2;border:1px solid #FCA5A5;border-radius:12px;padding:16px 20px;margin:20px 0">
        <p style="margin:0;font-size:14px;color:#7F1D1D">Product</p>
        <p style="margin:4px 0 0;font-size:18px;font-weight:700;color:#7F1D1D">{product_name}</p>
        <p style="margin:6px 0 0;font-size:13px;color:#7F1D1D">SKU: <code>{product_sku}</code></p>
        <p style="margin:10px 0 0;font-size:14px;color:#7F1D1D">
          Current stock: <strong>{current_stock}</strong> &nbsp;·&nbsp; Minimum: <strong>{minimum_stock}</strong>
        </p>
      </div>
      <p>Please restock this product as soon as possible.</p>
      <p style="color:#6B9E8A;font-size:12px">This alert was triggered automatically by StockFlow CRM.</p>
    </body></html>
    """
    _send(to_email, subject, html)
