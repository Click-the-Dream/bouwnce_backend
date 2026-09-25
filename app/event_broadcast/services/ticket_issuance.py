"""Ticket code generation, QR rendering, and Cloudinary upload.

Design constraints:
- Codes are globally unique (unique index on ``event_tickets.code``); a
  collision retries with fresh randomness instead of failing the fulfillment.
- QR images are a nice-to-have: ticket validity must never depend on QR
  generation or the Cloudinary upload succeeding, so failures degrade to a
  codes-only email and are logged, never raised.
- The QR encodes a verification URI (not raw digits) embedding both the
  ticket code and the purchaser's user id, so a client scan carries enough
  information to fetch ticket details for verification.
"""

import io
import logging
import secrets

from app.core.config import settings
from app.event_broadcast.models.event_ticket import EventTicket
from app.utils.cloudinary_utils import upload_image
from app.utils.exception import BadRequestException

logger = logging.getLogger(__name__)

CODE_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
CODE_LENGTH = 10
_CODE_GENERATION_ROUNDS = 10
TICKET_VERIFY_URI_PREFIX = "verify://ticket/"
TICKET_VERIFY_USER_PARAM = "u"


def build_ticket_verify_uri(code: str, user_id: str) -> str:
    """QR payload for one ticket: ``verify://ticket/<code>?u=<user_id>``.

    Single source of truth for the format — ``normalize_ticket_code`` is the
    matching parser, so the two cannot drift. The user id lets a scanning
    client fetch the full ticket details for verification.
    """
    return f"{TICKET_VERIFY_URI_PREFIX}{code}?{TICKET_VERIFY_USER_PARAM}={user_id}"


class IssueTicketError(Exception):
    """Ticket issuance could not complete (e.g. code space exhausted)."""


def normalize_ticket_code(raw_code: str) -> str:
    """Normalize a scanned/typed ticket code to its bare code form.

    Accepts the bare code, the legacy QR URI (``verify://ticket/<code>``),
    or the current QR URI embedding the purchaser (``verify://ticket/<code>
    ?u=<user_id>``). Raises ``BadRequestException`` for anything else so
    garbage input fails at the boundary instead of turning into a pointless
    DB lookup.
    """
    code = raw_code.strip()
    if code.startswith(TICKET_VERIFY_URI_PREFIX):
        code, _, query = code[len(TICKET_VERIFY_URI_PREFIX) :].partition("?")
        if query:
            params = dict(param.partition("=")[::2] for param in query.split("&"))
            if (
                TICKET_VERIFY_USER_PARAM not in params
                or not params[TICKET_VERIFY_USER_PARAM]
            ):
                raise BadRequestException(
                    "Invalid ticket QR payload: missing purchaser id"
                )
    code = code.strip("/")
    if not code.isalnum() or len(code) != CODE_LENGTH:
        raise BadRequestException(
            "Invalid ticket code format. Pass the 10-digit code or the decoded QR URI"
        )
    return code


async def generate_ticket_codes(db, count: int) -> list[str]:
    """Generate ``count`` unique 10-digit codes, skipping existing ones.

    Collision handling: regenerate the colliding codes and re-check, up to a
    bounded number of rounds. 1e10 code space makes collisions rare; the cap
    exists to fail loudly instead of spinning if the table is somehow huge.
    """
    codes: list[str] = []
    for _ in range(_CODE_GENERATION_ROUNDS):
        while len(codes) < count:
            candidate = "".join(
                secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH)
            )
            if candidate not in codes:
                codes.append(candidate)

        existing = await EventTicket.count_codes_existing(db, codes)
        if not existing:
            return codes
        codes = [code for code in codes if code not in existing]

    raise IssueTicketError("Could not generate unique ticket codes")


def generate_ticket_qr_png(code: str, user_id: str) -> bytes | None:
    """Render a QR PNG encoding ``verify://ticket/<code>?u=<user_id>``.

    ``segno`` is an optional dependency: if it is not installed the ticket is
    still fully valid (codes-only email); we just ship without the image.
    """
    try:
        import segno  # noqa: PLC0415  (optional dependency)

        buffer = io.BytesIO()
        segno.make(build_ticket_verify_uri(code, user_id)).save(
            buffer, kind="png", scale=8
        )
        return buffer.getvalue()
    except Exception:
        logger.warning(
            "QR generation unavailable for ticket code (segno missing or failed); "
            "issuing ticket without a QR image"
        )
        return None


async def _upload_qr_png(code: str, png_bytes: bytes) -> str | None:
    """Upload one QR image to Cloudinary, returning its secure URL or None."""
    import tempfile  # noqa: PLC0415  (small, local to this helper)

    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(png_bytes)
            path = tmp.name
        result = await upload_image(path, settings.EVENT_TICKET_QR_FOLDER)
        return result["url"] if result else None
    except Exception:
        logger.warning("QR upload to Cloudinary failed for ticket code %s", code)
        return None


async def create_tickets_with_qr(
    db,
    *,
    attendance,
    selections: list[dict],
) -> list[EventTicket]:
    """Build and insert one ticket row per purchased unit.

    ``selections`` is the attendance's ``ticket_info``: a list of
    ``{ticket_name, price, quantity, ...}`` line items. Each unit gets its own
    row with its own code; QR upload failure degrades to ``qr_code_url=None``.
    """
    total_units = sum(int(selection["quantity"]) for selection in selections)
    codes = await generate_ticket_codes(db, total_units)

    ticket_rows: list[dict] = []
    for selection in selections:
        unit_amount = float(selection["price"])
        for _ in range(int(selection["quantity"])):
            ticket_rows.append(
                {
                    "attendance_id": attendance.id,
                    "event_id": attendance.event_id,
                    "user_id": attendance.user_id,
                    "ticket_name": str(selection["ticket_name"]),
                    "code": codes.pop(),
                    "unit_amount": unit_amount,
                    "status": "valid",
                }
            )

    ticket_models = await EventTicket.create_tickets(db, ticket_rows)

    for ticket_model in ticket_models:
        png = generate_ticket_qr_png(ticket_model.code, str(attendance.user_id))
        if png is None:
            continue
        ticket_model.qr_code_url = await _upload_qr_png(ticket_model.code, png)

    return ticket_models
