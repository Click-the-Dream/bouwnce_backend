from pydantic import BaseModel, Field
from typing import Annotated

class BusinessInfoBase(BaseModel):
    name: Annotated[str, Field(min_length=2, examples=["John's Store"])]
    address: Annotated[str, Field(min_length=5, examples=["123 Main St, City, Country"])]
    phone_number: Annotated[str, Field(min_length=7, examples=["+1234567890"])]
    email: Annotated[str, Field(min_length=5, examples=["john@example.com"])]
    

class BusinessInfoCreate(BusinessInfoBase):
    user_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    btype: Annotated[str, Field(min_length=2, examples=["Retail"])]

class BusinessInfoResponse(BusinessInfoBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    user_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]

class BusinessInfoUpdate(BaseModel):
    name: Annotated[str | None, Field(min_length=2, examples=["John's Store"])] = None
    address: Annotated[str | None, Field(min_length=5, examples=["123 Main St, City, Country"])] = None
    phone_number: Annotated[str | None, Field(min_length=7, examples=["+1234567890"])] = None
    email: Annotated[str | None, Field(min_length=5, examples=["john@example.com"])] = None
    btype: Annotated[str | None, Field(min_length=2, examples=["Retail"])] = None    

class BusinessInfoDelete(BaseModel):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]