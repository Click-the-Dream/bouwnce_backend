from typing import Annotated

from pydantic import BaseModel, Field

from app.utils.responses import BaseResponse


class NewsLetterBase(BaseModel):
    name: Annotated[str, Field(..., description="Name of the newsletter")]
    description: Annotated[str, Field(..., description="Description of the newsletter")]
    subject: Annotated[str, Field(..., description="Subject of the newsletter")]
    content: Annotated[str, Field(..., description="Content of the newsletter")]


class NewsLetterCreate(NewsLetterBase):
    pass


class NewsLetterUpdate(BaseModel):
    name: Annotated[str | None, Field(None, description="Name of the newsletter")]
    description: Annotated[
        str | None, Field(None, description="Description of the newsletter")
    ]
    subject: Annotated[str | None, Field(None, description="Subject of the newsletter")]
    content: Annotated[str | None, Field(None, description="Content of the newsletter")]


class NewsLetterResponseSchema(NewsLetterBase):
    id: Annotated[str, Field(..., description="ID of the newsletter")]
    is_sent: Annotated[
        bool, Field(..., description="Whether the newsletter has been sent")
    ]
    send_at: Annotated[
        str | None, Field(..., description="Scheduled time to send the newsletter")
    ] = None
    status: Annotated[str, Field(..., description="Status of the newsletter")]
    created_at: Annotated[
        str, Field(..., description="Creation time of the newsletter")
    ]
    updated_at: Annotated[
        str, Field(..., description="Last update time of the newsletter")
    ]


class NewsLetterResponse(BaseResponse):
    data: Annotated[
        NewsLetterResponseSchema, Field(..., description="Newsletter response data")
    ]


class PaginatedNewsLetterResponseSchema(BaseModel):
    newsletters: Annotated[
        list[NewsLetterResponseSchema],
        Field(..., description="List of newsletter response"),
    ]
    page: Annotated[int, Field(..., description="Current page number")]
    page_size: Annotated[int, Field(..., description="Number of items per page")]
    total: Annotated[int, Field(..., description="Total number of newsletters")]


class PaginatedNewsLetterResponse(BaseResponse):
    data: Annotated[
        PaginatedNewsLetterResponseSchema,
        Field(..., description="Paginated newsletter response data"),
    ]
