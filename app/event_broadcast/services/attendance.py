import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.event_broadcast.models.attendance import UserEventAttendance
from app.event_broadcast.models.event_ticket import EventTicket
from app.event_broadcast.models.events import EventState, OutingEvent
from app.event_broadcast.schemas.attendance import AttendanceSchema
from app.event_broadcast.services.ticket_issuance import (
    create_tickets_with_qr,
    normalize_ticket_code,
)
from app.matching_ground.model.user_interest import UserInterest
from app.models.user import User
from app.service.payment.paystack import paystack_service
from app.utils.emails import generate_email_content, send_email
from app.utils.exception import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    GoneException,
    NotFoundException,
)
from app.utils.helper import is_valid_uuid
from app.utils.money import naira_to_kobo
from app.utils.responses import response_builder
from app.worker.event_system import (
    EventAttendancePaymentCompletedEvent,
    EventNames,
    MobileEvent,
    PushNotificationEvent,
    dispatch_event,
)

logger = logging.getLogger(__name__)


def _serialize_attendance(attendance: UserEventAttendance) -> dict[str, Any]:
    attendance_dict = attendance.to_dict()
    attendance_dict["user_id"] = str(attendance_dict["user_id"])
    attendance_dict["event_id"] = str(attendance_dict["event_id"])
    return attendance_dict


def _serialize_event(event: OutingEvent) -> dict[str, Any]:
    event_dict = event.to_dict()
    event_dict["state"] = (
        event.state.value if hasattr(event.state, "value") else event.state
    )
    event_dict["location_type"] = (
        event.location_type.value
        if hasattr(event.location_type, "value")
        else event.location_type
    )
    event_dict["id"] = str(event_dict["id"])
    event_dict["creator_id"] = str(event_dict["creator_id"])
    return event_dict


class AttendanceService:
    async def explore_events(
        self,
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        keyword: str | None = None,
        date: str | None = None,
        location: str | None = None,
    ) -> dict[str, Any]:
        if page < 1:
            raise BadRequestException("Page must be a positive integer")
        if page_size < 1 or page_size > 100:
            raise BadRequestException("Page size must be between 1 and 100")

        user_interests = await UserInterest.get_user_interests(db, current_user.id)
        user_interest_names = [interest.name for interest in user_interests]

        base_query = select(OutingEvent).where(
            OutingEvent.state == EventState.LIVE,
            OutingEvent.is_deleted == False,  # noqa: E712
        )

        if keyword:
            keyword_filter = or_(
                OutingEvent.name.ilike(f"%{keyword}%"),
                OutingEvent.desc.ilike(f"%{keyword}%"),
                OutingEvent.interests.astext.ilike(f"%{keyword}%"),
            )
            base_query = base_query.where(keyword_filter)

        if date:
            try:
                event_date = datetime.fromisoformat(date).date()
                base_query = base_query.where(func.date(OutingEvent.date) == event_date)
            except ValueError:
                raise BadRequestException(
                    "Invalid date format. Use ISO format (YYYY-MM-DD)"
                ) from None

        if location:
            base_query = base_query.where(OutingEvent.location.ilike(f"%{location}%"))

        base_query = base_query.order_by(OutingEvent.created_at.desc())
        result = await db.execute(base_query)
        all_live_events = list(result.scalars().all())

        if user_interest_names and all_live_events:
            matched = []
            unmatched = []
            for event in all_live_events:
                event_interests = event.interests or []
                if any(i in event_interests for i in user_interest_names):
                    matched.append(event)
                else:
                    unmatched.append(event)
            ordered_events = matched + unmatched
        else:
            ordered_events = all_live_events

        total = len(ordered_events)
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        offset = (page - 1) * page_size
        paginated = ordered_events[offset : offset + page_size]

        response = response_builder(
            status_code=status.HTTP_200_OK,
            message="Events fetched successfully",
            data=[_serialize_event(e) for e in paginated],
        )
        response["page"] = page
        response["page_size"] = page_size
        response["total_pages"] = total_pages
        response["total_events"] = total
        return response

    async def claim_attendance(
        self,
        db: AsyncSession,
        current_user: User,
        event_id: str,
        ticket_info: list[AttendanceSchema],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Claim attendance (event checkout).

        Idempotent: a request replayed with the same ``Idempotent-key`` header
        returns the originally created attendance (and its payment URL)
        instead of minting a second Paystack transaction. A user whose claim
        is still ``pending`` (e.g. abandoned checkout) may retry; the retry
        replays the stored Paystack reference/URL so the charge and the row
        stay 1:1. Only a ``successful`` claim is final.
        """
        if not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        event = await OutingEvent.get_event_by_id(db, event_id)
        if not event:
            raise NotFoundException("Event not found")

        if event.state != EventState.LIVE:
            raise BadRequestException("Can only claim attendance for live events")

        # ``outing_events.date`` is a naive DateTime column in PG; normalize
        # before comparing so a naive value can't raise TypeError here.
        event_date = event.date
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=UTC)
        if event_date <= datetime.now(UTC):
            raise BadRequestException("Cannot claim attendance for a past event")

        if not ticket_info or not isinstance(ticket_info, list):
            raise BadRequestException("ticket_info must be a non-empty list")

        if idempotency_key:
            # Replay safety: same key must return the original result, whatever
            # ticket selection it was created with.
            replayed = await UserEventAttendance.get_by_idempotency_key(
                db, idempotency_key
            )
            if replayed:
                if str(replayed.user_id) != str(current_user.id):
                    raise ForbiddenException(message="Idempotency key already in use")
                return response_builder(
                    status_code=status.HTTP_201_CREATED,
                    message="Attendance claim already processed",
                    data=_serialize_attendance(replayed),
                )

        total_amount = 0.0
        total_tickets = 0

        event_ticket = event.ticket_info
        if not event_ticket and ticket_info:
            raise ConflictException("Event Does not have Ticket information provided")

        event_ticket = {ticket["ticket_name"]: ticket for ticket in event_ticket}
        user_select_tickets = []

        for i, ticket in enumerate(ticket_info):
            ticket_name = ticket.ticket_name.strip()
            if not ticket_name:
                raise BadRequestException(f"Ticket at index {i} requires a ticket_name")

            quantity = ticket.quantity
            if quantity < 1:
                raise BadRequestException(
                    f"Ticket at index {i} must have quantity >= 1"
                )
            event_ticket_data = event_ticket.get(ticket_name)
            if not event_ticket_data:
                raise BadRequestException(f"Event does not have Ticket: {ticket_name}")

            user_select_tickets.append({**event_ticket_data, "quantity": quantity})

            total_amount += event_ticket_data["price"] * quantity
            total_tickets += quantity

        if total_tickets > settings.MAX_EVENT_TICKETS_PER_CLAIM:
            raise BadRequestException(
                f"Cannot claim more than "
                f"{settings.MAX_EVENT_TICKETS_PER_CLAIM} tickets per event"
            )

        # Advisory per-ticket-type availability: capacity is optional per
        # type (None = unlimited) and a binding check re-runs at fulfillment
        # under the event row lock, so this is early feedback only.
        requested_by_type: dict[str, int] = {}
        for selection in user_select_tickets:
            name = str(selection["ticket_name"])
            requested_by_type[name] = requested_by_type.get(name, 0) + int(
                selection["quantity"]
            )
        capacities = {
            str(t.get("ticket_name")): t.get("capacity")
            for t in (event.ticket_info or [])
        }
        if any(cap is not None for cap in capacities.values()):
            issued_by_type = await OutingEvent.count_issued_by_type(db, str(event.id))
            for type_name, requested in requested_by_type.items():
                cap = capacities.get(type_name)
                if cap is None:
                    continue
                remaining = int(cap) - issued_by_type.get(type_name, 0)
                if requested > remaining:
                    raise ConflictException(
                        f"Not enough {type_name} tickets remaining: "
                        f"requested {requested}, available {max(remaining, 0)}"
                    )

        attendance = await UserEventAttendance.check_existing_attendance(
            db, current_user.id, event_id
        )
        if attendance and attendance.payment_status == "successful":
            raise BadRequestException(
                "You have already claimed attendance for this event"
            )

        if total_amount > 0:
            if attendance and attendance.payment_reference:
                # Retry of a failed/unpaid claim: replay the stored Paystack
                # transaction so the reference and this row stay 1:1 (minting
                # a second reference here would orphan any charge made on the
                # first one, since the webhook resolves rows by reference).
                payment_url = attendance.payment_url
                payment_reference = None  # already persisted on the row
            else:
                try:
                    (
                        payment_url,
                        payment_reference,
                    ) = paystack_service.create_payment_intent(
                        {
                            "email": current_user.email,
                            "amount": naira_to_kobo(total_amount),
                            "metadata": {
                                "type": "event",
                                "event_id": str(event.id),
                                "quantity": total_tickets,
                                "user_id": str(current_user.id),
                            },
                        }
                    )
                except Exception as exc:
                    # Nothing is persisted on this path, so there is no row to
                    # mark failed; the retried request simply tries Paystack
                    # again (the session rolls back on the raised exception).
                    raise BadRequestException(
                        "Unable to initialize event payment"
                    ) from exc
        else:
            payment_url = None
            payment_reference = None

        if attendance is None:
            # Persist the Paystack pair on creation itself. Omitting these
            # keys here left fresh rows with NULLs, which the response echoed
            # and — critically — which the reference-keyed webhook could
            # never match, so fulfillment never fired for new claims. For
            # free events (total_amount == 0) both are None by design.
            attendance_data = {
                "user_id": current_user.id,
                "event_id": event_id,
                "ticket_info": user_select_tickets,
                "total_amount": total_amount,
                "total_tickets": total_tickets,
                "payment_status": "pending",
                "attendance_status": "pending_payment",
                "idempotency_key": idempotency_key,
                "payment_url": payment_url,
                "payment_reference": payment_reference,
            }
            attendance = await UserEventAttendance.create_attendance(
                db, attendance_data
            )
        else:
            # Retry of a pending claim: refresh the selection/totals; the
            # reference/URL are only overwritten when Paystack generated a new
            # one (the replay case above leaves the stored pair untouched).
            attendance.ticket_info = user_select_tickets
            attendance.total_amount = total_amount
            attendance.total_tickets = total_tickets
            if payment_reference:
                attendance.payment_reference = payment_reference
            if payment_url:
                attendance.payment_url = payment_url

        if idempotency_key:
            attendance.idempotency_key = idempotency_key

        if total_amount == 0:
            attendance.payment_status = "successful"
            attendance.attendance_status = "confirmed"

        await db.commit()
        await db.refresh(attendance)

        return response_builder(
            status_code=status.HTTP_201_CREATED,
            message="Attendance claimed successfully",
            data=_serialize_attendance(attendance),
        )

    async def verify_event_payment(
        self, db: AsyncSession, redis, current_user: User, attendance_id: str
    ) -> dict[str, Any]:
        attendance = await UserEventAttendance.get_by_id(attendance_id, db)
        if str(attendance.user_id) != str(current_user.id):
            raise BadRequestException("You cannot verify this event payment")
        if attendance.payment_status == "successful":
            return response_builder(
                status_code=status.HTTP_200_OK,
                message="Event payment already verified",
                data=_serialize_attendance(attendance),
            )
        if not attendance.payment_reference:
            raise BadRequestException("This attendance has no pending payment")

        paid, payload = paystack_service.callback(attendance.payment_reference)
        if not paid:
            raise BadRequestException("Event payment was not successful")
        await dispatch_event(
            EventNames.EVENT_ATTENDANCE_PAYMENT_COMPLETED,
            EventAttendancePaymentCompletedEvent(
                attendance_id=str(attendance.id),
                reference=attendance.payment_reference,
                amount_kobo=int(payload.get("amount", 0)),
            ),
            db=db,
            redis=redis,
        )
        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Event payment verified successfully",
            data=_serialize_attendance(attendance),
        )

    async def handle_paystack_webhook(
        self, db: AsyncSession, redis, request
    ) -> dict[str, Any] | None:
        await paystack_service.verify_webhook_signature(request)
        body = await request.json()
        if body.get("event") != "charge.success":
            return None
        data = body.get("data") or {}
        reference = str(data.get("reference") or "")
        if not reference:
            return None
        attendance = await UserEventAttendance.get_by_payment_reference(db, reference)
        if attendance is None:
            return None
        paid, verified_payment = await asyncio.to_thread(
            paystack_service.callback, reference
        )
        if not paid:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Event payment is awaiting verification",
            )
        # Same-session fulfillment (capacity check + ticket issuance + email).
        # Raising propagates a non-200 to Paystack so it retries; the
        # reconciliation beat task is the recovery net either way.
        await self.fulfill_event_tickets(
            db,
            redis,
            attendance,
            amount_kobo=int(verified_payment.get("amount") or 0),
        )
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Event payment processed",
            data=_serialize_attendance(attendance),
        )

    async def fulfill_event_tickets(
        self,
        db: AsyncSession,
        redis,
        attendance: UserEventAttendance,
        amount_kobo: int | None = None,
    ) -> list[EventTicket]:
        """Issue tickets and send the delivery email for a paid attendance.

        Caller contract: the attendance row is already locked, its reference
        resolved, and the charge verified with Paystack. When ``amount_kobo``
        is provided it is re-checked against the stored total (defense against
        tampered/stale checkouts). The caller commits (or rolls back) the
        session this runs in, so the capacity decrement, the status
        transition, and the ticket insert are all-or-nothing. Raising here
        lets the webhook return non-200 (Paystack retries) and the reconcile
        task retry on its next beat.
        """
        if amount_kobo is not None and naira_to_kobo(attendance.total_amount) != int(
            amount_kobo
        ):
            raise ConflictException(message="Event payment amount mismatch")
        result = await db.execute(
            select(OutingEvent)
            .where(
                OutingEvent.id == attendance.event_id,
                OutingEvent.is_deleted.is_(False),
            )
            .with_for_update()
        )
        event = result.scalar_one_or_none()
        if event is None:
            raise ValueError(
                f"Event not found for ticket fulfillment: {attendance.event_id}"
            )

        # Binding per-ticket-type capacity check, under the event row lock.
        # Types with capacity None are uncapped. Payment has already
        # succeeded at this point; on shortfall we withhold tickets and
        # surface loudly for ops (refund/waitlist is a pending business
        # decision), leaving the payment record intact.
        capacities = {
            str(t.get("ticket_name")): t.get("capacity")
            for t in (event.ticket_info or [])
        }
        if any(cap is not None for cap in capacities.values()):
            requested_by_type: dict[str, int] = {}
            for selection in attendance.ticket_info:
                name = str(selection["ticket_name"])
                requested_by_type[name] = requested_by_type.get(name, 0) + int(
                    selection["quantity"]
                )
            issued_by_type = await OutingEvent.count_issued_by_type(db, str(event.id))
            shortfalls: list[str] = []
            for type_name, requested in requested_by_type.items():
                cap = capacities.get(type_name)
                if cap is None:
                    continue
                remaining = int(cap) - issued_by_type.get(type_name, 0)
                if requested > remaining:
                    shortfalls.append(
                        f"{type_name}: requested {requested}, "
                        f"available {max(remaining, 0)}"
                    )
            if shortfalls:
                logger.error(
                    "Per-type ticket capacity exceeded after payment; tickets "
                    "withheld attendance_id=%s event_id=%s shortfalls=%s",
                    attendance.id,
                    event.id,
                    "; ".join(shortfalls),
                )
                if redis is not None:
                    await dispatch_event(
                        EventNames.PUSH_NOTIFICATION,
                        PushNotificationEvent(
                            user_id=str(attendance.user_id),
                            title="Event sold out",
                            body=(
                                "Your payment succeeded but the event is sold "
                                "out. Our team will contact you about a refund."
                            ),
                            data={
                                "type": "event.payment.sold_out",
                                "attendance_id": str(attendance.id),
                                "event_id": str(event.id),
                            },
                        ),
                        db=db,
                        redis=redis,
                    )
                return []

        # Status transition first: any re-entering webhook/reconcile replay
        # sees ``successful`` and short-circuits instead of double-issuing.
        attendance.payment_status = "successful"
        attendance.attendance_status = "confirmed"
        await attendance.save(db)

        tickets = await create_tickets_with_qr(
            db, attendance=attendance, selections=attendance.ticket_info
        )

        # Email is best-effort by design: ticket rows are already part of this
        # transaction, so a failed email must not roll the purchase back. The
        # user can always retrieve tickets via the attendance endpoints.
        email_sent = await self._send_ticket_delivery_email(db, attendance, tickets)
        if not email_sent:
            logger.error(
                "Ticket delivery email failed; tickets remain valid and "
                "retrievable via API attendance_id=%s",
                attendance.id,
            )

        if redis is not None:
            event_payload = {
                "user_id": str(attendance.user_id),
                "attendance_id": str(attendance.id),
                "event_id": str(attendance.event_id),
                "ticket_count": len(tickets),
            }
            await dispatch_event(
                EventNames.MOBILE_EVENT,
                MobileEvent(event_name="event.tickets.issued", payload=event_payload),
                db=db,
                redis=redis,
            )
            await dispatch_event(
                EventNames.PUSH_NOTIFICATION,
                PushNotificationEvent(
                    user_id=str(attendance.user_id),
                    title="Your tickets are ready",
                    body=f"Your tickets for {event.name} are ready.",
                    data={"type": "event.tickets.issued", **event_payload},
                ),
                db=db,
                redis=redis,
            )

        return tickets

    @staticmethod
    async def _send_ticket_delivery_email(
        db: AsyncSession, attendance: UserEventAttendance, tickets: list[EventTicket]
    ) -> bool:
        try:
            user = await User.get_by_id(str(attendance.user_id), db)
            event = await OutingEvent.get_event_by_id(db, str(attendance.event_id))
            if user is None or event is None:
                logger.error(
                    "Cannot send ticket email: user or event missing attendance_id=%s",
                    attendance.id,
                )
                return False

            email_data = generate_email_content(
                subject="Your event tickets",
                template_name="event_tickets.html",
                context={
                    "user_name": user.username or user.full_name,
                    "event_name": event.name,
                    "event_date": event.date.isoformat() if event.date else "",
                    "total_tickets": len(tickets),
                    "tickets": [
                        {
                            "code": ticket.code,
                            "ticket_name": ticket.ticket_name,
                            "qr_code_url": ticket.qr_code_url or "",
                        }
                        for ticket in tickets
                    ],
                    "year": datetime.now(UTC).year,
                },
            )
            return await send_email(
                email_to=user.email,
                subject=email_data.subject,
                html_content=email_data.html_content,
            )
        except Exception:
            logger.exception(
                "Ticket delivery email raised attendance_id=%s", attendance.id
            )
            return False

    async def get_user_attendance(
        self,
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        event_id: str | None = None,
        name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        event_type: str | None = None,
    ) -> dict[str, Any]:
        if page < 1:
            raise BadRequestException("Page must be a positive integer")
        if page_size < 1 or page_size > 100:
            raise BadRequestException("Page size must be between 1 and 100")

        if event_type and event_type not in ("past", "upcoming"):
            raise BadRequestException("event_type must be 'past' or 'upcoming'")
        if event_id and not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        if date_from:
            try:
                datetime.fromisoformat(date_from)
            except ValueError:
                raise BadRequestException(
                    "Invalid date_from format. Use ISO format (YYYY-MM-DD)"
                ) from None

        if date_to:
            try:
                datetime.fromisoformat(date_to)
            except ValueError:
                raise BadRequestException(
                    "Invalid date_to format. Use ISO format (YYYY-MM-DD)"
                ) from None

        result = await UserEventAttendance.get_user_attendance(
            db=db,
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            event_id=event_id,
            name=name,
            date_from=date_from,
            date_to=date_to,
            event_type=event_type,
        )

        serialized = []
        for attendance in result["attendances"]:
            attendance_dict = _serialize_attendance(attendance)
            serialized.append(attendance_dict)

        response = response_builder(
            status_code=status.HTTP_200_OK,
            message="Attendance fetched successfully",
            data=serialized,
        )
        response["page"] = result["page"]
        response["page_size"] = result["page_size"]
        response["total_pages"] = result["total_pages"]
        response["total_attendances"] = result["total"]
        return response

    async def get_event_attendees(
        self,
        db: AsyncSession,
        current_user: User,
        event_id: str,
        page: int = 1,
        page_size: int = 10,
        username: str | None = None,
        interest: str | None = None,
    ) -> dict[str, Any]:
        if not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        if page < 1:
            raise BadRequestException("Page must be a positive integer")
        if page_size < 1 or page_size > 100:
            raise BadRequestException("Page size must be between 1 and 100")

        event = await OutingEvent.get_event_by_id(db, event_id)
        if not event:
            raise NotFoundException("Event not found")

        result = await UserEventAttendance.get_event_attendees(
            db=db,
            event_id=event_id,
            page=page,
            page_size=page_size,
            username=username,
            interest=interest,
        )

        serialized = []
        for attendance in result["attendances"]:
            attendance_dict = _serialize_attendance(attendance)
            if attendance.user:
                attendance_dict["user"] = {
                    "id": str(attendance.user.id),
                    "username": attendance.user.username,
                    "full_name": attendance.user.full_name,
                    "profile_image": attendance.user.profile_pic,
                }
            serialized.append(attendance_dict)

        response = response_builder(
            status_code=status.HTTP_200_OK,
            message="Attendees fetched successfully",
            data=serialized,
        )
        response["page"] = result["page"]
        response["page_size"] = result["page_size"]
        response["total_pages"] = result["total_pages"]
        response["total_attendees"] = result["total"]
        return response

    async def get_user_tickets(
        self,
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        event_id: str | None = None,
        ticket_status: str | None = None,
    ) -> dict[str, Any]:
        """List the current user's event tickets, newest first, with event summary."""
        if page < 1:
            raise BadRequestException("Page must be a positive integer")
        if page_size < 1 or page_size > 100:
            raise BadRequestException("Page size must be between 1 and 100")
        if event_id and not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")
        if ticket_status and ticket_status not in ("valid", "used", "void"):
            raise BadRequestException("status must be one of: valid, used, void")

        result = await EventTicket.get_user_tickets(
            db=db,
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            event_id=event_id,
            status=ticket_status,
        )

        serialized = []
        for ticket in result["tickets"]:
            event = ticket.event
            serialized.append(
                {
                    "id": str(ticket.id),
                    "code": ticket.code,
                    "qr_code_url": ticket.qr_code_url,
                    "status": ticket.status,
                    "ticket_name": ticket.ticket_name,
                    "unit_amount": ticket.unit_amount,
                    "used_at": ticket.used_at,
                    "created_at": ticket.created_at,
                    "event": {
                        "id": str(event.id),
                        "name": event.name,
                        "date": event.date,
                        "location": event.location,
                        "banner_url": event.banner_url,
                    },
                }
            )

        response = response_builder(
            status_code=status.HTTP_200_OK,
            message="Tickets fetched successfully",
            data=serialized,
        )
        response["page"] = result["page"]
        response["page_size"] = result["page_size"]
        response["total_pages"] = result["total_pages"]
        response["total_tickets"] = result["total"]
        return response

    async def verify_ticket(
        self,
        db: AsyncSession,
        current_user: User,
        event_id: str,
        raw_code: str,
    ) -> dict[str, Any]:
        """Verify a ticket at the door (event owner only).

        Order of checks: authorization first (cheapest, least disclosure),
        then event existence, then the idempotent status response, then the
        atomic claim. Double-tap safe: the claim is a single conditional
        UPDATE, so two rapid calls can never both flip the same ticket.
        """
        if not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        event = await OutingEvent.get_event_by_id(db, event_id)
        if not event:
            raise NotFoundException("Event not found")
        if str(event.creator_id) != str(current_user.id):
            raise ForbiddenException("Only the event owner can verify tickets")

        code = normalize_ticket_code(raw_code)

        ticket = await EventTicket.get_by_code(db, code, with_attendance=True)
        if not ticket or str(ticket.event_id) != str(event.id):
            raise NotFoundException("Ticket not found for this event")

        if ticket.status == "used":
            return self._ticket_already_used_response(ticket)
        if ticket.status == "void":
            raise GoneException("Ticket has been voided")

        attendance = ticket.attendance
        if attendance and attendance.payment_status != "successful":
            raise ConflictException("Ticket payment is not confirmed; contact support")

        used_at = datetime.now(UTC)
        claimed = await EventTicket.claim_for_verification(
            db,
            code=code,
            event_id=str(event.id),
            verifier_id=str(current_user.id),
            used_at=used_at,
        )
        if not claimed:
            lost_race = await EventTicket.get_by_code(db, code, with_attendance=True)
            if lost_race and lost_race.status == "used":
                return self._ticket_already_used_response(lost_race)
            raise NotFoundException("Ticket not found for this event")

        response = response_builder(
            status_code=status.HTTP_200_OK,
            message="Ticket verified successfully",
            data={
                "code": ticket.code,
                "status": "used",
                "used_at": used_at,
                "used_by": str(current_user.id),
                "ticket_name": ticket.ticket_name,
                "unit_amount": ticket.unit_amount,
                "attendee": self._serialize_ticket_attendee(ticket),
            },
        )
        # Build the payload before committing: commit may expire ORM state,
        # and lazy-loading it back in async context would fail.
        await db.commit()
        return response

    def _ticket_already_used_response(self, ticket: EventTicket) -> dict[str, Any]:
        """200-with-context response for a re-scan of an already-used ticket."""
        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Ticket already used",
            data={
                "code": ticket.code,
                "status": ticket.status,
                "used_at": ticket.used_at,
                "used_by": str(ticket.used_by) if ticket.used_by else None,
                "ticket_name": ticket.ticket_name,
                "attendee": self._serialize_ticket_attendee(ticket),
            },
        )

    @staticmethod
    def _serialize_ticket_attendee(ticket: EventTicket) -> dict[str, Any] | None:
        """Attendee info for door staff; None when relationships are not loaded."""
        attendance = ticket.__dict__.get("attendance")
        if attendance is None:
            return None
        attendee = attendance.__dict__.get("user")
        if attendee is None:
            return None
        return {
            "id": str(attendee.id),
            "username": attendee.username,
            "full_name": attendee.full_name,
            "email": attendee.email,
            "profile_image": attendee.profile_pic,
            "ticket_name": ticket.ticket_name,
            "quantity": 1,
        }

    async def cancel_attendance(
        self,
        db: AsyncSession,
        current_user: User,
        event_id: str,
    ) -> dict[str, Any]:
        if not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        event = await OutingEvent.get_event_by_id(db, event_id)
        if not event:
            raise NotFoundException("Event not found")

        attendance = await UserEventAttendance.check_existing_attendance(
            db, current_user.id, event_id
        )

        if not attendance:
            raise NotFoundException("Attendance record not found")
        if attendance.payment_status == "successful":
            raise BadRequestException(
                "Paid event attendance cannot be cancelled without a refund"
            )

        attendance = await UserEventAttendance.cancel_attendance(
            db, current_user.id, event_id
        )

        await db.commit()

        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Attendance cancelled successfully",
            data=_serialize_attendance(attendance),
        )


attendance_service = AttendanceService()
