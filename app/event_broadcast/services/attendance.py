from datetime import datetime
from typing import Any

from fastapi import status
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.event_broadcast.models.attendance import UserEventAttendance
from app.event_broadcast.models.events import EventState, OutingEvent
from app.matching_ground.model.user_interest import UserInterest
from app.models.user import User
from app.utils.exception import BadRequestException, NotFoundException
from app.utils.helper import is_valid_uuid
from app.utils.responses import response_builder


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

        user_interests = await UserInterest.get_user_interests(db, str(current_user.id))
        user_interest_names = [interest.name for interest in user_interests]

        base_query = select(OutingEvent).where(
            OutingEvent.state == EventState.LIVE.value,
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
                datetime.fromisoformat(date)
                base_query = base_query.where(
                    OutingEvent.date.cast(text("DATE")) == text(f"'{date}'")
                )
            except ValueError:
                raise BadRequestException(
                    "Invalid date format. Use ISO format (YYYY-MM-DD)"
                )

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
        ticket_info: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        event = await OutingEvent.get_event_by_id(db, event_id)
        if not event:
            raise NotFoundException("Event not found")

        if event.state != EventState.LIVE.value:
            raise BadRequestException("Can only claim attendance for live events")

        if not ticket_info or not isinstance(ticket_info, list):
            raise BadRequestException("ticket_info must be a non-empty list")

        total_amount = 0.0
        total_tickets = 0

        for i, ticket in enumerate(ticket_info):
            if not isinstance(ticket, dict):
                raise BadRequestException(f"Ticket at index {i} must be an object")

            ticket_name = ticket.get("ticket_name")
            if not ticket_name:
                raise BadRequestException(f"Ticket at index {i} requires a ticket_name")

            price = ticket.get("price")
            if price is None or price < 0:
                raise BadRequestException(
                    f"Ticket at index {i} must have a non-negative price"
                )

            quantity = ticket.get("quantity", 1)
            if quantity < 1:
                raise BadRequestException(
                    f"Ticket at index {i} must have quantity >= 1"
                )

            ticket["quantity"] = quantity
            total_amount += price * quantity
            total_tickets += quantity

        existing = await UserEventAttendance.check_existing_attendance(
            db, str(current_user.id), event_id
        )
        if existing:
            raise BadRequestException(
                "You have already claimed attendance for this event"
            )

        attendance_data = {
            "user_id": str(current_user.id),
            "event_id": event_id,
            "ticket_info": ticket_info,
            "total_amount": total_amount,
            "total_tickets": total_tickets,
            "payment_status": "pending",
            "attendance_status": "confirmed",
        }

        attendance = await UserEventAttendance.create_attendance(db, attendance_data)
        await db.commit()

        return response_builder(
            status_code=status.HTTP_201_CREATED,
            message="Attendance claimed successfully",
            data=_serialize_attendance(attendance),
        )

    async def get_user_attendance(
        self,
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
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

        if date_from:
            try:
                datetime.fromisoformat(date_from)
            except ValueError:
                raise BadRequestException(
                    "Invalid date_from format. Use ISO format (YYYY-MM-DD)"
                )

        if date_to:
            try:
                datetime.fromisoformat(date_to)
            except ValueError:
                raise BadRequestException(
                    "Invalid date_to format. Use ISO format (YYYY-MM-DD)"
                )

        result = await UserEventAttendance.get_user_attendance(
            db=db,
            user_id=str(current_user.id),
            page=page,
            page_size=page_size,
            name=name,
            date_from=date_from,
            date_to=date_to,
            event_type=event_type,
        )

        serialized = []
        for attendance in result["attendances"]:
            attendance_dict = _serialize_attendance(attendance)
            if attendance.event:
                attendance_dict["event"] = _serialize_event(attendance.event)
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
                    "email": attendance.user.email,
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


attendance_service = AttendanceService()
