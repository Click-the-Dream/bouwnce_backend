from pydantic import BaseModel, Field
from typing import Annotated


class PayoutInfoBase(BaseModel):
    account_name: Annotated[str, Field(min_length=2, examples=["John Doe"])]
    account_number: Annotated[str, Field(min_length=5, examples=["123456789"])]
    bank_name: Annotated[str, Field(min_length=2, examples=["Bank of World"])]
    
class PayoutInfoCreate(PayoutInfoBase):
   pass

class PayoutInfoResponse(PayoutInfoBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    user_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]
    
class PayoutInfoUpdate(BaseModel):
    account_name: Annotated[str | None, Field(min_length=2, examples=["John Doe"])] = None
    account_number: Annotated[str | None, Field(min_length=5, examples=["123456789"])] = None
    bank_name: Annotated[str | None, Field(min_length=2, examples=["Bank of World"])] = None
