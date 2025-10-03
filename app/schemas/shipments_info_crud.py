from pydantic import BaseModel, Field
from typing import Annotated


class ShipmentsInfoBase(BaseModel):
    shipping_address: Annotated[str, Field(min_length=5, examples=["123 Main St, City, Country"])]
    delivery_method: Annotated[str, Field(min_length=2, examples=["Standard", "Express"])]
    delivery_fee: Annotated[str, Field(min_length=1, examples=["5.00", "10.00"])]
    delivery_time: Annotated[str, Field(min_length=2, examples=["3-5 business days", "1-2 business days"])]

class ShipmentsInfoCreate(ShipmentsInfoBase):
    pass

class ShipmentsInfoResponse(ShipmentsInfoBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    user_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]

class ShipmentsInfoUpdate(BaseModel):
    shipping_address: Annotated[str | None, Field(min_length=5, examples=["123 Main St, City, Country"])] = None
    delivery_method: Annotated[str | None, Field(min_length=2, examples=["Standard", "Express"])] = None
    delivery_fee: Annotated[str | None, Field(min_length=1, examples=["5.00", "10.00"])] = None
    delivery_time: Annotated[str | None, Field(min_length=2, examples=["3-5 business days", "1-2 business days"])] = None
