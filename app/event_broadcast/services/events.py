from datetime import datetime
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.event_broadcast.models.events import EventState, LocationType, OutingEvent
from app.models.user import User
from app.utils.exception import BadRequestException, NotFoundException
from app.utils.helper import is_valid_uuid
from app.utils.responses import response_builder

VALID_LOCATION_TYPES = {lt.value for lt in LocationType}
VALID_STATES = {es.value for es in EventState}


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


class EventService:
    async def create_event(
        self, db: AsyncSession, current_user: User, event_data: dict
    ) -> dict[str, Any]:
        if not event_data.get("name") or not event_data["name"].strip():
            raise BadRequestException("Event name is required")

        if not event_data.get("desc") or not event_data["desc"].strip():
            raise BadRequestException("Event description is required")

        if not event_data.get("date"):
            raise BadRequestException("Event date is required")

        try:
            event_data["date"] = datetime.fromisoformat(event_data["date"])
        except (ValueError, TypeError):
            raise BadRequestException(
                "Invalid date format. Use ISO format (e.g. 2026-12-31T20:00:00)"
            ) from None

        if event_data.get("price") is None or event_data["price"] < 0:
            raise BadRequestException("Price must be a non-negative number")

        if not event_data.get("location") or not event_data["location"].strip():
            raise BadRequestException("Event location is required")

        location_type = event_data.get("location_type")
        if not location_type or location_type not in VALID_LOCATION_TYPES:
            raise BadRequestException(
                f"Invalid location_type. Must be one of: {', '.join(sorted(VALID_LOCATION_TYPES))}"
            )

        event_data["location_type"] = LocationType(location_type)

        if location_type in {"hybrid", "virtual"} and (
            not event_data.get("link") or not event_data["link"].strip()
        ):
            raise BadRequestException(
                "Event link is required for Hybrid or Virtual event"
            )

        if not event_data.get("banner_url") or not event_data["banner_url"].strip():
            raise BadRequestException("Banner URL is required")

        state = event_data.get("state", EventState.DRAFT.value)
        if state not in VALID_STATES:
            raise BadRequestException(
                f"Invalid state. Must be one of: {', '.join(sorted(VALID_STATES))}"
            )
        event_data["state"] = EventState(state)

        ticket_info = event_data.get("ticket_info")
        if ticket_info is not None:
            if not isinstance(ticket_info, list):
                raise BadRequestException("ticket_info must be a list")
            for i, ticket in enumerate(ticket_info):
                if isinstance(ticket, dict):
                    ticket_info[i] = {
                        "ticket_name": ticket.get("ticket_name", ""),
                        "price": ticket.get("price", 0),
                        "ticket_description": ticket.get("ticket_description"),
                    }
                    if not ticket_info[i]["ticket_name"]:
                        raise BadRequestException(
                            f"Ticket at index {i} requires a ticket_name"
                        )
                    if ticket_info[i]["price"] is None or ticket_info[i]["price"] < 0:
                        raise BadRequestException(
                            f"Ticket at index {i} must have a non-negative price"
                        )
            event_data["ticket_info"] = ticket_info

        interests = event_data.get("interests")
        if interests is not None:
            if not isinstance(interests, list):
                raise BadRequestException("interests must be a list of strings")
            event_data["interests"] = [str(i) for i in interests]

        event_data["creator_id"] = str(current_user.id)

        event = await OutingEvent.create_event(db, event_data)
        await db.commit()

        return response_builder(
            status_code=status.HTTP_201_CREATED,
            message="Event created successfully",
            data=_serialize_event(event),
        )

    async def get_user_events(
        self,
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        status_filter: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        if page < 1:
            raise BadRequestException("Page must be a positive integer")
        if page_size < 1 or page_size > 100:
            raise BadRequestException("Page size must be between 1 and 100")

        if status_filter and status_filter not in VALID_STATES:
            raise BadRequestException(
                f"Invalid status filter. Must be one of: {', '.join(sorted(VALID_STATES))}"
            )

        result = await OutingEvent.get_events_by_creator(
            db=db,
            creator_id=str(current_user.id),
            page=page,
            page_size=page_size,
            status=status_filter,
            name=name,
        )

        serialized_events = [_serialize_event(e) for e in result["events"]]

        response = response_builder(
            status_code=status.HTTP_200_OK,
            message="Events fetched successfully",
            data=serialized_events,
        )
        response["page"] = result["page"]
        response["page_size"] = result["page_size"]
        response["total_pages"] = result["total_pages"]
        response["total_events"] = result["total"]
        return response

    async def get_event_by_id(self, db: AsyncSession, event_id: str) -> dict[str, Any]:
        if not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        event = await OutingEvent.get_event_by_id(db, event_id)
        if not event:
            raise NotFoundException("Event not found")

        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Event fetched successfully",
            data=_serialize_event(event),
        )

    async def update_event(
        self,
        db: AsyncSession,
        current_user: User,
        event_id: str,
        update_data: dict,
    ) -> dict[str, Any]:
        if not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        event = await OutingEvent.get_event_by_id(db, event_id)
        if not event:
            raise NotFoundException("Event not found")

        if str(event.creator_id) != str(current_user.id):
            raise BadRequestException("You are not authorized to update this event")

        clean_data = {k: v for k, v in update_data.items() if v is not None}

        if "name" in clean_data and not clean_data["name"].strip():
            raise BadRequestException("Event name cannot be empty")

        if "desc" in clean_data and not clean_data["desc"].strip():
            raise BadRequestException("Event description cannot be empty")

        if "date" in clean_data:
            try:
                datetime.fromisoformat(clean_data["date"])
            except (ValueError, TypeError):
                raise BadRequestException(
                    "Invalid date format. Use ISO format (e.g. 2026-12-31T20:00:00)"
                ) from None

        if "price" in clean_data and (
            clean_data["price"] is None or clean_data["price"] < 0
        ):
            raise BadRequestException("Price must be a non-negative number")

        if "location" in clean_data and not clean_data["location"].strip():
            raise BadRequestException("Event location cannot be empty")

        if (
            "location_type" in clean_data
            and clean_data["location_type"] not in VALID_LOCATION_TYPES
        ):
            raise BadRequestException(
                f"Invalid location_type. Must be one of: {', '.join(sorted(VALID_LOCATION_TYPES))}"
            )

        if "link" in clean_data and not clean_data["link"].strip():
            raise BadRequestException("Event link cannot be empty")

        if "banner_url" in clean_data and not clean_data["banner_url"].strip():
            raise BadRequestException("Banner URL cannot be empty")

        if "ticket_info" in clean_data:
            ticket_info = clean_data["ticket_info"]
            if not isinstance(ticket_info, list):
                raise BadRequestException("ticket_info must be a list")
            for i, ticket in enumerate(ticket_info):
                if isinstance(ticket, dict):
                    if not ticket.get("ticket_name"):
                        raise BadRequestException(
                            f"Ticket at index {i} requires a ticket_name"
                        )
                    if ticket.get("price") is None or ticket["price"] < 0:
                        raise BadRequestException(
                            f"Ticket at index {i} must have a non-negative price"
                        )

        if "interests" in clean_data:
            if not isinstance(clean_data["interests"], list):
                raise BadRequestException("interests must be a list of strings")
            clean_data["interests"] = [str(i) for i in clean_data["interests"]]

        if "state" in clean_data:
            raise BadRequestException(
                "Use the update status endpoint to change event state"
            )

        updated_event = await OutingEvent.update_event(db, event_id, clean_data)
        await db.commit()

        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Event updated successfully",
            data=_serialize_event(updated_event),
        )

    async def update_event_status(
        self,
        db: AsyncSession,
        current_user: User,
        event_id: str,
        new_state: str,
    ) -> dict[str, Any]:
        if not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        if new_state not in VALID_STATES:
            raise BadRequestException(
                f"Invalid state. Must be one of: {', '.join(sorted(VALID_STATES))}"
            )

        event = await OutingEvent.get_event_by_id(db, event_id)
        if not event:
            raise NotFoundException("Event not found")

        if str(event.creator_id) != str(current_user.id):
            raise BadRequestException("You are not authorized to update this event")

        state_enum = EventState(new_state)
        updated_event = await OutingEvent.update_event_status(db, event_id, state_enum)
        await db.commit()

        return response_builder(
            status_code=status.HTTP_200_OK,
            message=f"Event status updated to {new_state} successfully",
            data=_serialize_event(updated_event),
        )

    async def delete_event(
        self, db: AsyncSession, current_user: User, event_id: str
    ) -> dict[str, Any]:
        if not is_valid_uuid(event_id):
            raise BadRequestException("Invalid event ID format")

        event = await OutingEvent.get_event_by_id(db, event_id)
        if not event:
            raise NotFoundException("Event not found")

        if str(event.creator_id) != str(current_user.id):
            raise BadRequestException("You are not authorized to delete this event")

        await OutingEvent.delete_event(db, event_id)
        await db.commit()

        return response_builder(
            status_code=status.HTTP_200_OK,
            message="Event deleted successfully",
        )


event_service = EventService()
