import enum
from typing import Annotated

from pydantic import BaseModel, Field

from app.utils.responses import BaseResponse


class StatusEnum(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class VerificationBase(BaseModel):
    type: Annotated[str, Field(examples=["NIN"])]
    id_number: Annotated[
        str, Field(min_length=11, max_length=11, examples=["123456789"])
    ]


class VerificationCreate(VerificationBase):
    pass


class VerificationResponseSchema(VerificationBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    status: Annotated[
        StatusEnum, Field(description="The status of the NIN verification")
    ]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class VerificationResponse(BaseResponse):
    data: Annotated[
        VerificationResponseSchema, Field(description="Verification response data")
    ]


class VerificationUpdate(BaseModel):
    type: Annotated[str | None, Field(examples=["NIN"])] = None
    id_number: Annotated[str | None, Field(examples=["123456789"])] = None
