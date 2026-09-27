"""Ticket-confirmation PDF generation.

Produces one PDF per purchase (attendance), mirroring the product sample:
event header, one block per ticket unit (name, code, quantity), the ticket
owner section, and a support footer. Each block embeds a locally rendered QR
(``verify://ticket/<code>?u=<user_id>``) so verification never depends on
Cloudinary being reachable.

Design constraints:
- Pure function over loaded ORM objects + ticket rows: no DB access, trivially
  unit-testable.
- Returns ``bytes``; the caller decides delivery (email attachment today).
- Never raises for cosmetic reasons is NOT the goal — it can raise, but the
  email sender treats PDF failure as non-fatal (codes-only email still goes
  out), mirroring the QR degradation rule.
"""

import io
import logging
import re
from datetime import datetime

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from segno import make_qr

from app.event_broadcast.services.ticket_issuance import build_ticket_verify_uri

logger = logging.getLogger(__name__)

PAGE_WIDTH, PAGE_HEIGHT = A4
_MARGIN = 48
_TEXT_COLOR = HexColor("#1F2937")
_MUTED_COLOR = HexColor("#6B7280")
_ROW_BORDER_COLOR = HexColor("#E5E7EB")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "event"


def _format_event_date(event_date: datetime) -> str:
    """``outing_events.date`` may be naive; render it as-is, wall-clock."""
    return event_date.strftime("%Y-%m-%d")


def _draw_qr(
    canvas: Canvas, code: str, user_id: str, x: float, y: float, size: float
) -> None:
    buffer = io.BytesIO()
    make_qr(build_ticket_verify_uri(code, user_id)).save(buffer, kind="png", scale=4)
    buffer.seek(0)
    canvas.drawImage(ImageReader(buffer), x, y, width=size, height=size)


def _ticket_block(
    canvas: Canvas,
    *,
    ticket_name: str,
    code: str,
    user_id: str,
    y: float,
) -> float:
    """Draw one ticket block; returns the new y cursor below it."""
    block_height = 132
    top = y
    bottom = top - block_height
    label_x = _MARGIN + 16
    value_x = _MARGIN + 200
    qr_size = 84
    qr_x = PAGE_WIDTH - _MARGIN - qr_size - 16
    qr_y = top - qr_size - 16

    canvas.setStrokeColor(_ROW_BORDER_COLOR)
    canvas.setLineWidth(1)
    canvas.roundRect(_MARGIN, bottom, PAGE_WIDTH - 2 * _MARGIN, block_height, 8)

    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(_MUTED_COLOR)
    canvas.drawString(label_x, top - 28, "Ticket Name")
    canvas.drawString(label_x, top - 62, "Ticket Code")
    canvas.drawString(label_x, top - 96, "Available slots")

    canvas.setFont("Helvetica-Bold", 12)
    canvas.setFillColor(_TEXT_COLOR)
    canvas.drawString(value_x, top - 28, ticket_name[:38])
    canvas.setFont("Courier-Bold", 14)
    canvas.drawString(value_x, top - 63, code)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(value_x, top - 96, "1")

    try:
        _draw_qr(canvas, code, user_id, qr_x, qr_y, qr_size)
    except Exception:
        # QR in the PDF is best-effort exactly like the QR in the email:
        # the code itself is always printed and remains authoritative.
        logger.warning("PDF QR render failed for ticket code %s", code)

    return bottom - 18


def build_tickets_pdf(
    *,
    event_name: str,
    event_date: datetime,
    event_location: str,
    owner_name: str,
    owner_email: str,
    tickets: list[dict],
    support_email: str | None = None,
    support_phone: str | None = None,
) -> bytes:
    """Render the purchase-confirmation PDF for one attendance.

    ``tickets`` is a list of ``{ticket_name, code}`` dicts — one entry per
    ticket unit, each with its own code (one code per ticket).
    """
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4, pageCompression=1)
    canvas.setTitle("Ticket Confirmation")

    y = PAGE_HEIGHT - _MARGIN

    canvas.setFillColor(_TEXT_COLOR)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(_MARGIN, y, event_name[:52])
    y -= 24

    canvas.setFillColor(_MUTED_COLOR)
    canvas.setFont("Helvetica", 11)
    canvas.drawString(_MARGIN, y, f"Start Date - {_format_event_date(event_date)}")
    y -= 18
    time_label = event_date.strftime("%Y-%m-%d %H:%M")
    canvas.drawString(_MARGIN, y, time_label)
    y -= 18
    canvas.drawString(_MARGIN, y, event_location[:80])
    y -= 36

    canvas.setFillColor(_TEXT_COLOR)
    canvas.setFont("Helvetica", 12)
    canvas.drawString(_MARGIN, y, f"Hey {owner_name[:48]},")
    y -= 18
    canvas.setFillColor(_MUTED_COLOR)
    canvas.drawString(_MARGIN, y, "This is your order confirmation for this event.")
    y -= 34

    canvas.setFillColor(_TEXT_COLOR)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(_MARGIN, y, "Ticket Details")
    y -= 22

    for ticket in tickets:
        if y < _MARGIN + 320:
            canvas.showPage()
            y = PAGE_HEIGHT - _MARGIN
        y = _ticket_block(
            canvas,
            ticket_name=str(ticket["ticket_name"]),
            code=str(ticket["code"]),
            user_id=str(ticket.get("user_id", "")),
            y=y,
        )

    y -= 16
    if y < _MARGIN + 120:
        canvas.showPage()
        y = PAGE_HEIGHT - _MARGIN

    canvas.setFillColor(_TEXT_COLOR)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(_MARGIN, y, "Ticket Owner")
    y -= 20
    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(_MUTED_COLOR)
    canvas.drawString(_MARGIN + 8, y, f"Name: {owner_name[:64]}")
    y -= 16
    canvas.drawString(_MARGIN + 8, y, f"Email address: {owner_email[:64]}")

    y = _MARGIN + 18
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(_MUTED_COLOR)
    contact_bits = ["Need help? Contact our support team:"]
    if support_email:
        contact_bits.append(support_email)
    if support_phone:
        contact_bits.append(support_phone)
    canvas.drawString(_MARGIN, y, "  ".join(contact_bits))

    canvas.save()
    return buffer.getvalue()


def ticket_pdf_filename(event_name: str) -> str:
    return f"{_slugify(event_name)}-tickets.pdf"
