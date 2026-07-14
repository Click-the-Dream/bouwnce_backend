from typing import Annotated

from pydantic import BaseModel, Field

from app.utils.responses import BaseResponse


class CreateEventSchema(BaseModel):
    name: Annotated[str, Field(description="Name of the event")]
    desc: Annotated[str, Field(description="Description of the event")]
    date: Annotated[str, Field(description="Date of the event in ISO format")]
    price: Annotated[float, Field(description="Price of the event")]
    location: Annotated[str, Field(description="Location of the event")]
    link: Annotated[str, Field(description="Link to the event")]
    banner_url: Annotated[str, Field(description="Banner URL of the event")]
    state: Annotated[str, Field(description="State of the event (draft/live)")]
    interests: Annotated[
        list[str], Field(description="List of interests for the event")
    ]


class EventResponseSchema(BaseModel):
    name: Annotated[str, Field(description="Name of the event")]
    desc: Annotated[str, Field(description="Description of the event")]
    date: Annotated[str, Field(description="Date of the event in ISO format")]
    price: Annotated[float, Field(description="Price of the event")]
    location: Annotated[str, Field(description="Location of the event")]
    link: Annotated[str, Field(description="Link to the event")]
    banner_url: Annotated[str, Field(description="Banner URL of the event")]
    state: Annotated[str, Field(description="State of the event (draft/live)")]
    interests: Annotated[
        list[str], Field(description="List of interests for the event")
    ]


class EventResponse(BaseResponse):
    data: Annotated[EventResponseSchema, Field(description="Details of the event")]


class PaginatedEventListResponse(BaseResponse):
    data: Annotated[
        list[EventResponseSchema], Field(description="Paginated list of events")
    ]
    page: Annotated[int, Field(description="Current page number")]
    page_size: Annotated[int, Field(description="Number of events per page")]
    total_pages: Annotated[int, Field(description="Total number of pages")]
    total_events: Annotated[int, Field(description="Total number of events")]
