from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.utils.responses import BaseResponse


class TicketSchema(BaseModel):
    ticket_name: Annotated[str, Field(description="Name of the ticket")]
    price: Annotated[float, Field(description="Price of the ticket")]
    ticket_description: Annotated[
        str | None, Field(default=None, description="Description of the ticket")
    ]


class CreateEventSchema(BaseModel):
    name: Annotated[str, Field(description="Name of the event")]
    desc: Annotated[str, Field(description="Description of the event")]
    date: Annotated[str, Field(description="Date of the event in ISO format")]
    price: Annotated[float, Field(description="Price of the event")]
    location: Annotated[str, Field(description="Location of the event")]
    location_type: Annotated[
        str, Field(description="Location type: physical, virtual, or hybrid")
    ]
    link: Annotated[str | None, Field(description="Link to the event")] = None
    banner_url: Annotated[str, Field(description="Banner URL of the event")]
    state: Annotated[str, Field(description="State of the event (draft/live)")]
    ticket_info: Annotated[
        list[TicketSchema] | None,
        Field(default=None, description="List of ticket types for the event"),
    ]
    interests: Annotated[
        list[str] | None,
        Field(default=None, description="List of interest tags for the event"),
    ]


class UpdateEventSchema(BaseModel):
    name: Annotated[str | None, Field(default=None, description="Name of the event")]
    desc: Annotated[
        str | None, Field(default=None, description="Description of the event")
    ]
    date: Annotated[
        str | None, Field(default=None, description="Date of the event in ISO format")
    ]
    price: Annotated[
        float | None, Field(default=None, description="Price of the event")
    ]
    location: Annotated[
        str | None, Field(default=None, description="Location of the event")
    ]
    location_type: Annotated[
        str | None,
        Field(default=None, description="Location type: physical, virtual, or hybrid"),
    ]
    link: Annotated[str | None, Field(default=None, description="Link to the event")]
    banner_url: Annotated[
        str | None, Field(default=None, description="Banner URL of the event")
    ]
    ticket_info: Annotated[
        list[TicketSchema] | None,
        Field(default=None, description="List of ticket types for the event"),
    ]
    interests: Annotated[
        list[str] | None,
        Field(default=None, description="List of interest tags for the event"),
    ]


class UpdateEventStatusSchema(BaseModel):
    state: Annotated[str, Field(description="New state of the event (draft/live)")]


class EventResponseData(BaseModel):
    id: str
    name: str
    desc: str
    date: str
    price: float
    location: str
    location_type: str
    link: str | None
    banner_url: str
    state: str
    ticket_info: list[dict[str, Any]] | None = None
    interests: list[str] | None = None
    creator_id: str
    created_at: str
    updated_at: str


class EventResponse(BaseResponse):
    data: Annotated[EventResponseData, Field(description="Details of the event")]


class PaginatedEventListResponse(BaseResponse):
    data: Annotated[
        list[EventResponseData], Field(description="Paginated list of events")
    ]
    page: Annotated[int, Field(description="Current page number")]
    page_size: Annotated[int, Field(description="Number of events per page")]
    total_pages: Annotated[int, Field(description="Total number of pages")]
    total_events: Annotated[int, Field(description="Total number of events")]
