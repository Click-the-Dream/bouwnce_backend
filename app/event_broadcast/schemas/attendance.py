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


class AttendanceResponseSchema(BaseModel):
    user_id: Annotated[str, Field(..., description="User id")]
    event_id: Annotated[str, Field(..., description="Event Id")]
    ticket_info: Annotated[
        list[TicketSchema], Field(description="List of user purchased tickets")
    ]
    total_amount: Annotated[int, Field(ge=0, description="total cost of the ticket")]
    total_tickets: Annotated[
        int, Field(ge=0, description="Total number of ticket purchased")
    ]
    payment_status: Annotated[
        str, Field(default="pending", description="Status of payment")
    ]
    attendance_status: Annotated[
        str, Field(default="confirmed", description="Event Attendance status")
    ]


class AttendanceResponse(BaseResponse):
    data: Annotated[AttendanceResponseSchema, Field(description="Attendance Data")]


class PaginatedEventListResponse(BaseResponse):
    data: Annotated[
        list[AttendanceResponseSchema], Field(description="Paginated list of events")
    ]
    page: Annotated[int, Field(description="Current page number")]
    page_size: Annotated[int, Field(description="Number of events per page")]
    total_pages: Annotated[int, Field(description="Total number of pages")]
    total_attendances: Annotated[int, Field(description="Total number of events")]
