from pydantic import BaseModel, Field
from typing import Annotated


class StoreInfoBase(BaseModel):
    store_logo: Annotated[str, Field(min_length=5, examples=["https://example.com/logo.png"])]
    store_banner: Annotated[str | None, Field(min_length=5, examples=["https://example.com/banner.png"])] = None
    store_description: Annotated[str, Field(min_length=10, examples=["This is a great store."])]
    
class StoreInfoCreate(StoreInfoBase):
    pass
    
class StoreInfoResponse(StoreInfoBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    user_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]

class StoreInfoUpdate(BaseModel):
    store_logo: Annotated[str | None, Field(min_length=5, examples=["https://example.com/logo.png"])] = None
    store_banner: Annotated[str | None, Field(min_length=5, examples=["https://example.com/banner.png"])] = None
    store_description: Annotated[str | None, Field(min_length=10, examples=["This is a great store."])] = None
