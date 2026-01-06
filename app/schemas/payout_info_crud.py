from typing import Annotated

from pydantic import BaseModel, Field

from app.utils.responses import BaseResponse


class PayoutInfoBase(BaseModel):
    account_name: Annotated[str, Field(min_length=2, examples=["John Doe"])]
    account_number: Annotated[str, Field(min_length=5, examples=["123456789"])]
    bank_name: Annotated[str, Field(min_length=2, examples=["Bank of World"])]
    security_question: Annotated[
        str, Field(min_length=5, examples=["What is your pet's name?"])
    ]
    security_answer: Annotated[str, Field(min_length=2, examples=["Fluffy"])]
    withdrawal_pin: Annotated[
        str, Field(min_length=6, max_length=6, examples=["123456"])
    ]


class PayoutInfoCreate(PayoutInfoBase):
    pass


class PayoutInfoResponseSchema(PayoutInfoBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    store_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class PayoutInfoResponse(BaseResponse):
    data: Annotated[
        PayoutInfoResponseSchema, Field(description="Payout info response data")
    ]


class PayoutInfoUpdate(BaseModel):
    account_name: Annotated[str | None, Field(min_length=2, examples=["John Doe"])] = (
        None
    )
    account_number: Annotated[
        str | None, Field(min_length=5, examples=["123456789"])
    ] = None
    bank_name: Annotated[
        str | None, Field(min_length=2, examples=["Bank of World"])
    ] = None
    security_question: Annotated[
        str | None, Field(min_length=5, examples=["What is your pet's name?"])
    ] = None
    security_answer: Annotated[str | None, Field(min_length=2, examples=["Fluffy"])] = (
        None
    )
    withdrawal_pin: Annotated[
        str | None, Field(min_length=6, max_length=6, examples=["123456"])
    ] = None
