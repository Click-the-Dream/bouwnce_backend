from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime

from app.utils.responses import BaseResponse


class ShipmentsInfoBase(BaseModel):
    shipping_address: Annotated[
        str, Field(min_length=5, examples=["123 Main St, City, Country"])
    ]
    delivery_method: Annotated[
        str, Field(min_length=2, examples=["Standard", "Express"])
    ]
    delivery_fee: Annotated[str, Field(min_length=1, examples=["5.00", "10.00"])]
    delivery_time: Annotated[
        str, Field(min_length=2, examples=["3-5 business days", "1-2 business days"])
    ]
    


class ShipmentsInfoCreate(ShipmentsInfoBase):
    pass


class ShipmentsInfoResponseSchema(ShipmentsInfoBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    store_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class StoreShipmentsInfoResponseSchema(BaseModel):
    store_name: Annotated[str, Field(examples=["John's Store"])]
    store_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    shipment_info: Annotated[
        list[ShipmentsInfoResponseSchema], Field(description="Shipment info list")
    ]


class StoreShipmentsInfoResponse(BaseResponse):
    data: Annotated[
        list[StoreShipmentsInfoResponseSchema],
        Field(description="Store shipments info response data"),
    ]


class ShipmentsInfoResponse(BaseResponse):
    data: Annotated[
        list[ShipmentsInfoResponseSchema],
        Field(description="Shipments info response data"),
    ]


class ShipmentsInfoUpdate(BaseModel):
    shipping_address: Annotated[
        str | None, Field(min_length=5, examples=["123 Main St, City, Country"])
    ] = None
    delivery_method: Annotated[
        str | None, Field(min_length=2, examples=["Standard", "Express"])
    ] = None
    delivery_fee: Annotated[
        str | None, Field(min_length=1, examples=["5.00", "10.00"])
    ] = None
    delivery_time: Annotated[
        str | None,
        Field(min_length=2, examples=["3-5 business days", "1-2 business days"]),
    ] = None


class ShipmentsInfoDelete(BaseModel):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
