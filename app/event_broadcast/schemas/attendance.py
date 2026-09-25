from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.event_broadcast.schemas.events import TicketSchema
from app.utils.responses import BaseResponse


class AttendanceSchema(BaseModel):
    ticket_name: Annotated[str, Field(description="The ticket name to buy")]
    quantity: Annotated[
        int, Field(gt=0, description="total of that kind ticket to buy")
    ]


class ClaimAttendanceSchema(BaseModel):
    ticket_info: Annotated[
        list[AttendanceSchema], Field(..., description="List of tickets purchased")
    ]


class PurchasedTicketSchema(TicketSchema):
    quantity: int = Field(default=1, gt=0)


class AttendanceResponseSchema(BaseModel):
    id: Annotated[str, Field(..., description="Attendance id")]
    user_id: Annotated[str, Field(..., description="User id")]
    event_id: Annotated[str, Field(..., description="Event Id")]
    ticket_info: Annotated[
        list[PurchasedTicketSchema], Field(description="List of user purchased tickets")
    ]
    total_amount: Annotated[float, Field(ge=0, description="total cost of the ticket")]
    total_tickets: Annotated[
        int, Field(ge=0, description="Total number of ticket purchased")
    ]
    payment_status: Annotated[
        str, Field(default="pending", description="Status of payment")
    ]
    payment_reference: str | None = None
    payment_url: str | None = None
    attendance_status: Annotated[
        str, Field(default="confirmed", description="Event Attendance status")
    ]


class AttendanceResponse(BaseResponse):
    data: Annotated[AttendanceResponseSchema, Field(description="Attendance Data")]


class PaginatedAttendanceListResponse(BaseResponse):
    data: Annotated[
        list[AttendanceResponseSchema], Field(description="Paginated list of events")
    ]
    page: Annotated[int, Field(description="Current page number")]
    page_size: Annotated[int, Field(description="Number of events per page")]
    total_pages: Annotated[int, Field(description="Total number of pages")]
    total_attendances: Annotated[int, Field(description="Total number of events")]


class UserSchema(BaseModel):
    id: Annotated[str, Field(description="User Id")]
    username: Annotated[str, Field(description="User username")]
    full_name: Annotated[str, Field(description="User full name")]
    profile_image: dict | None = Field(
        default=None, description="User profile image, when one has been uploaded"
    )


class UserAttendanceResponseSchema(AttendanceResponseSchema):
    user: Annotated[UserSchema, Field(description="User data")]


class PaginatedUserAttendanceListResponse(BaseResponse):
    data: Annotated[
        list[UserAttendanceResponseSchema],
        Field(description="Paginated list of user attendees"),
    ]
    page: Annotated[int, Field(description="Current page number")]
    page_size: Annotated[int, Field(description="Number of events per page")]
    total_pages: Annotated[int, Field(description="Total number of pages")]
    total_attendees: Annotated[
        int, Field(description="Total number of user attending event")
    ]


class EventSummarySchema(BaseModel):
    id: Annotated[str, Field(description="Event id")]
    name: Annotated[str, Field(description="Event name")]
    date: Annotated[datetime, Field(description="Event date")]
    location: Annotated[str, Field(description="Event location")]
    banner_url: Annotated[str, Field(description="Event banner image URL")]


class EventTicketSchema(BaseModel):
    id: Annotated[str, Field(description="Ticket id")]
    code: Annotated[str, Field(description="Unique 10-digit ticket code")]
    qr_code_url: Annotated[
        str | None,
        Field(description="Cloudinary URL of the QR image, when generated"),
    ]
    status: Annotated[str, Field(description="Ticket status: valid, used, or void")]
    ticket_name: Annotated[str, Field(description="Name of the ticket tier")]
    unit_amount: Annotated[float, Field(description="Price paid for this ticket unit")]
    used_at: Annotated[
        datetime | None, Field(description="When the ticket was verified, if used")
    ]
    created_at: Annotated[datetime, Field(description="Purchase date")]
    event: Annotated[EventSummarySchema, Field(description="Event summary")]


class TicketVerificationSchema(BaseModel):
    code: Annotated[
        str,
        Field(
            description=(
                "10-digit ticket code or the decoded QR URI " "(verify://ticket/<code>)"
            )
        ),
    ]


class AttendeeInfoSchema(BaseModel):
    id: Annotated[str, Field(description="Attendee user id")]
    username: Annotated[str, Field(description="Attendee username")]
    full_name: Annotated[str, Field(description="Attendee full name")]
    email: Annotated[str, Field(description="Attendee email")]
    profile_image: dict | None = Field(
        default=None, description="Attendee profile image, when one has been uploaded"
    )
    ticket_name: Annotated[str, Field(description="Name of the ticket tier")]
    quantity: Annotated[int, Field(default=1, description="Tickets on this scan")]


class TicketVerificationDataSchema(BaseModel):
    code: Annotated[str, Field(description="The verified 10-digit ticket code")]
    status: Annotated[str, Field(description="Ticket status after the scan")]
    used_at: Annotated[
        datetime | None, Field(description="When the ticket was first verified")
    ]
    used_by: Annotated[str | None, Field(description="Verifier user id")]
    ticket_name: Annotated[str, Field(description="Name of the ticket tier")]
    unit_amount: Annotated[
        float | None, Field(description="Price paid for this ticket unit")
    ]
    attendee: Annotated[
        AttendeeInfoSchema | None,
        Field(description="Attendee info, when available for door staff"),
    ]


class TicketVerificationResponse(BaseResponse):
    data: Annotated[
        TicketVerificationDataSchema,
        Field(description="Verified ticket and attendee info"),
    ]


class PaginatedTicketListResponse(BaseResponse):
    data: Annotated[
        list[EventTicketSchema],
        Field(description="Paginated list of the user's event tickets"),
    ]
    page: Annotated[int, Field(description="Current page number")]
    page_size: Annotated[int, Field(description="Number of tickets per page")]
    total_pages: Annotated[int, Field(description="Total number of pages")]
    total_tickets: Annotated[int, Field(description="Total number of tickets")]
