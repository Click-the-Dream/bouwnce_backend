from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.schemas.contact_info_crud import ContactInfoResponseSchema
from app.schemas.payout_info_crud import PayoutInfoResponseSchema
from app.schemas.shipments_info_crud import ShipmentsInfoResponseSchema
from app.utils.responses import BaseResponse


class Image(BaseModel):
    public_id: Annotated[
        str, Field(examples=["a0e43d-1ccc-4370-a32e-41812280b26e/zjejpt55jhouwwwplllo"])
    ]
    url: Annotated[str, Field(examples=["http://image_url.png"])]


class StoreBase(BaseModel):
    name: Annotated[str, Field(min_length=2, examples=["My Awesome Store"])]
    address: Annotated[str, Field(examples=["123, Santos Street, Country"])]
    phone_number: Annotated[str, Field(examples=["12345678900"])]
    email: Annotated[str, Field(examples=["johndoe@example.com"])]


class StoreCreate(StoreBase):
    pass


class StoreResponseSchema(StoreBase):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    user_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    is_active: Annotated[bool, Field(examples=["true"])]
    store_description: Annotated[str | None, Field(examples=["This is the best Store"])]
    store_logo: Annotated[Image | None, Field(...)]
    store_banner: Annotated[Image | None, Field(...)]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class StoreResponse(BaseResponse):
    data: Annotated[StoreResponseSchema, Field(description="Store response data")]


class ListStoreResponse(BaseResponse):
    data: Annotated[
        list[StoreResponseSchema], Field(description="List of Store response")
    ]


class PaginateStoreResponseSchema(BaseModel):
    stores: Annotated[
        list[StoreResponseSchema], Field(description="List of Store Response")
    ]
    total: Annotated[int, Field(examples=[100])]
    page: Annotated[int, Field(examples=2)]
    page_size: Annotated[int, Field(examples=[10])]


class PaginatStoreResponse(BaseResponse):
    data: Annotated[
        PaginateStoreResponseSchema, Field(description="Paginated Store response")
    ]


class StoreFullDetailsResponseSchema(StoreResponseSchema):
    contact_info: ContactInfoResponseSchema | None = None
    payout_info: PayoutInfoResponseSchema | None = None
    shipment_info: list[ShipmentsInfoResponseSchema] | None = None


class StoreFullDetailsResponse(BaseResponse):
    data: Annotated[
        StoreFullDetailsResponseSchema,
        Field(description="Store full details response data"),
    ]


class StoreUpdate(BaseModel):
    name: Annotated[
        str | None, Field(min_length=2, examples=["My Even More Awesome Store"])
    ] = None
    address: Annotated[
        str | None, Field(min_length=5, examples=["123, Santos Street, Country"])
    ] = None
    phone_number: Annotated[
        str | None, Field(min_length=10, examples=["12345678900"])
    ] = None
    email: Annotated[EmailStr | None, Field(examples=["johndoe@exampl"])] = None


class StoreDelete(BaseModel):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
