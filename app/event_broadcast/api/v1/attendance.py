from typing import Any

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from app.api.dependencies import CurrentUser, dbSessionDep
from app.event_broadcast.schemas.attendance import (
    AttendanceResponse,
    BaseResponse,
    ClaimAttendanceSchema,
    PaginatedAttendanceListResponse,
)
from app.event_broadcast.schemas.events import PaginatedEventListResponse
from app.event_broadcast.services.attendance import attendance_service

router = APIRouter(prefix="/events")


@router.get(
    "/explore",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedEventListResponse,
    summary="Explore live events",
)
async def explore_events(
    db: dbSessionDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    keyword: str | None = Query(
        None, description="Search by name, description, or interests"
    ),
    date: str | None = Query(None, description="Filter by date (YYYY-MM-DD)"),
    location: str | None = Query(None, description="Filter by location"),
):
    return await attendance_service.explore_events(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        keyword=keyword,
        date=date,
        location=location,
    )


@router.post(
    "/{event_id}/attend",
    status_code=status.HTTP_201_CREATED,
    response_model=AttendanceResponse,
    summary="Claim attendance for an event",
)
async def claim_attendance(
    event_id: str,
    db: dbSessionDep,
    current_user: CurrentUser,
    attendance_data: ClaimAttendanceSchema,
):
    return await attendance_service.claim_attendance(
        db=db,
        current_user=current_user,
        event_id=event_id,
        ticket_info=attendance_data.ticket_info,
    )


@router.get(
    "/my-attendance",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedAttendanceListResponse,
    summary="Get user's event attendance",
)
async def get_my_attendance(
    db: dbSessionDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    name: str | None = Query(None, description="Search by event name"),
    date_from: str | None = Query(
        None, description="Filter events from date (YYYY-MM-DD)"
    ),
    date_to: str | None = Query(None, description="Filter events to date (YYYY-MM-DD)"),
    event_type: str | None = Query(
        None, description="Filter by event type (past/upcoming)"
    ),
):
    return await attendance_service.get_user_attendance(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        name=name,
        date_from=date_from,
        date_to=date_to,
        event_type=event_type,
    )


@router.get(
    "/{event_id}/attendees",
    status_code=status.HTTP_200_OK,
    summary="Get list of attendees for an event",
)
async def get_event_attendees(
    event_id: str,
    db: dbSessionDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    username: str | None = Query(None, description="Search by username"),
    interest: str | None = Query(None, description="Filter by interest"),
):
    return await attendance_service.get_event_attendees(
        db=db,
        current_user=current_user,
        event_id=event_id,
        page=page,
        page_size=page_size,
        username=username,
        interest=interest,
    )


@router.post(
    "/{event_id}/cancel",
    status_code=status.HTTP_200_OK,
    response_model=AttendanceResponse,
    summary="Cancel attendance for an event",
)
async def cancel_attendance(
    event_id: str,
    db: dbSessionDep,
    current_user: CurrentUser,
):
    return await attendance_service.cancel_attendance(
        db=db,
        current_user=current_user,
        event_id=event_id,
    )
