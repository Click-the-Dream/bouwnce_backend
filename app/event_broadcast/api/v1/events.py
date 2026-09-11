from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUser, dbSessionDep
from app.event_broadcast.schemas.events import (
    CreateEventSchema,
    EventResponse,
    PaginatedEventListResponse,
    UpdateEventSchema,
    UpdateEventStatusSchema,
)
from app.event_broadcast.services.events import event_service

router = APIRouter(prefix="/events")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=EventResponse,
    summary="Create a new event",
)
async def create_event(
    db: dbSessionDep,
    current_user: CurrentUser,
    event_data: CreateEventSchema,
):
    return await event_service.create_event(
        db=db,
        current_user=current_user,
        event_data=event_data.model_dump(),
    )


@router.get(
    "/my-events",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedEventListResponse,
    summary="Get list of events created by current user",
)
async def get_my_events(
    db: dbSessionDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (draft/live)"
    ),
    name: str | None = Query(None, description="Search by event name"),
):
    return await event_service.get_user_events(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        name=name,
    )


@router.get(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventResponse,
    summary="Get event by ID",
)
async def get_event_by_id(
    event_id: str,
    db: dbSessionDep,
):
    return await event_service.get_event_by_id(db=db, event_id=event_id)


@router.put(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventResponse,
    summary="Update an event",
)
async def update_event(
    event_id: str,
    db: dbSessionDep,
    current_user: CurrentUser,
    event_data: UpdateEventSchema,
):
    return await event_service.update_event(
        db=db,
        current_user=current_user,
        event_id=event_id,
        update_data=event_data.model_dump(exclude_unset=True),
    )


@router.patch(
    "/{event_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=EventResponse,
    summary="Update event status",
)
async def update_event_status(
    event_id: str,
    db: dbSessionDep,
    current_user: CurrentUser,
    status_data: UpdateEventStatusSchema,
):
    return await event_service.update_event_status(
        db=db,
        current_user=current_user,
        event_id=event_id,
        new_state=status_data.state,
    )


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an event",
)
async def delete_event(
    event_id: str,
    db: dbSessionDep,
    current_user: CurrentUser,
):
    return await event_service.delete_event(
        db=db,
        current_user=current_user,
        event_id=event_id,
    )
