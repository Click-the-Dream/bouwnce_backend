from fastapi import APIRouter, Query, Request, status

from app.api.dependencies import CurrentUser, dbSessionDep, redisSessionDep
from app.event_broadcast.schemas.attendance import (
    AttendanceResponse,
    ClaimAttendanceSchema,
    PaginatedAttendanceListResponse,
    PaginatedTicketListResponse,
    PaginatedUserAttendanceListResponse,
    TicketVerificationResponse,
    TicketVerificationSchema,
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
    request: Request,
    db: dbSessionDep,
    current_user: CurrentUser,
    attendance_data: ClaimAttendanceSchema,
):
    return await attendance_service.claim_attendance(
        db=db,
        current_user=current_user,
        event_id=event_id,
        ticket_info=attendance_data.ticket_info,
        idempotency_key=request.headers.get("Idempotent-key"),
    )


@router.post(
    "/attendance/{attendance_id}/payment/verify",
    status_code=status.HTTP_200_OK,
    response_model=AttendanceResponse,
    summary="Verify a paid event attendance with Paystack",
)
async def verify_event_payment(
    attendance_id: str,
    db: dbSessionDep,
    redis: redisSessionDep,
    current_user: CurrentUser,
):
    return await attendance_service.verify_event_payment(
        db=db, redis=redis, current_user=current_user, attendance_id=attendance_id
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
    "/my-payment-status",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedAttendanceListResponse,
    summary="Get current user's event payment statuses",
)
async def get_my_event_payment_statuses(
    db: dbSessionDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    event_id: str | None = Query(None, description="Event ID to filter by"),
):
    return await attendance_service.get_user_attendance(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        event_id=event_id,
    )


@router.get(
    "/my-tickets",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedTicketListResponse,
    summary="Get current user's event tickets",
)
async def get_my_tickets(
    db: dbSessionDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Tickets per page"),
    event_id: str | None = Query(None, description="Filter by event ID"),
    status: str | None = Query(
        None, description="Filter by ticket status (valid/used/void)"
    ),
):
    return await attendance_service.get_user_tickets(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        event_id=event_id,
        ticket_status=status,
    )


@router.post(
    "/{event_id}/tickets/verify",
    status_code=status.HTTP_200_OK,
    response_model=TicketVerificationResponse,
    summary="Verify a ticket for an event (event owner only)",
)
async def verify_ticket(
    event_id: str,
    db: dbSessionDep,
    current_user: CurrentUser,
    verify_data: TicketVerificationSchema,
):
    return await attendance_service.verify_ticket(
        db=db,
        current_user=current_user,
        event_id=event_id,
        raw_code=verify_data.code,
    )


@router.get(
    "/{event_id}/attendees",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedUserAttendanceListResponse,
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
