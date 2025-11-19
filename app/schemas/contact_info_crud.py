from typing import Annotated

from pydantic import BaseModel, Field


class ContactInfoBase(BaseModel):
    name: Annotated[str, Field(min_length=2, examples=["John Doe"])]
    title: Annotated[str | None, Field(min_length=2, examples=["Manager"])] = None
    email: Annotated[str, Field(min_length=5, examples=["john@example.com"])]
    phone_number: Annotated[str, Field(min_length=7, examples=["+1234567890"])]


class ContactInfoCreate(ContactInfoBase):
    pass


class ContactInfoResponse(ContactInfoBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    store_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class ContactInfoUpdate(BaseModel):
    name: Annotated[str | None, Field(min_length=2, examples=["John Doe"])] = None
    title: Annotated[str | None, Field(min_length=2, examples=["Manager"])] = None
    email: Annotated[str | None, Field(min_length=5, examples=["john@example.com"])] = (
        None
    )
    phone_number: Annotated[
        str | None, Field(min_length=7, examples=["+1234567890"])
    ] = None


class ContactInfoDelete(BaseModel):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
