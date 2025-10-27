from pydantic import BaseModel, Field
from typing import Annotated


class StoreInfoBase(BaseModel):
    store_logo: Annotated[str, Field(min_length=5, examples=["https://example.com/logo.png"])]
    address: Annotated[str, Field(min_length=5, examples=["123 Main St, Anytown, USA"])]
    phone_number: Annotated[str, Field(min_length=10, examples=["(123) 456-7890"])]
    email: Annotated[str, Field(min_length=5, examples=["info@example.com"])]
    
class StoreInfoCreate(StoreInfoBase):
    pass
    
class StoreInfoResponse(StoreInfoBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    user_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]

class StoreInfoUpdate(BaseModel):
    store_logo: Annotated[str | None, Field(min_length=5, examples=["https://example.com/logo.png"])] = None
    address: Annotated[str | None, Field(min_length=5, examples=["123 Main St, Anytown, USA"])] = None
    phone_number: Annotated[str | None, Field(min_length=10, examples=["(123) 456-7890"])] = None
    email: Annotated[str | None, Field(min_length=5, examples=["info@example.com"])] = None
