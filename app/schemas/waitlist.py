from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.utils.responses import BaseResponse


class WaitlistBase(BaseModel):
    email: Annotated[EmailStr, Field(examples=["johndoe@example.com"])]
    full_name: Annotated[str, Field(examples=["John Doe"])]
    phone_number: Annotated[
        str, Field(min_length=11, max_length=14, examples=["08145326543"])
    ]
    location: Annotated[str | None, Field(examples=["your Location"])] = None


class WaitlistCreate(WaitlistBase):
    pass


class WaitlistResponseSchema(WaitlistBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-10-22"])]
    updated_at: Annotated[str, Field(examples=["2025-11-10"])]


class WaitlistResponse(BaseResponse):
    data: Annotated[WaitlistResponseSchema, Field(description="Waitlist response data")]


class PaginatedWaitlistResponseSchema(BaseModel):
    waitlists: Annotated[
        list[WaitlistResponseSchema], Field(description="List of waitlist response")
    ]
    today_count: Annotated[int, Field(examples=[10])]
    page: Annotated[int, Field(examples=[2])]
    page_size: Annotated[int, Field(examples=[10])]
    total: Annotated[int, Field(examples=[100])]


class PaginatedWaitlistResponse(BaseResponse):
    data: Annotated[
        PaginatedWaitlistResponseSchema,
        Field(description="Paginated waitlist response"),
    ]
