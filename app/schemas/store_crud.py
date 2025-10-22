from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.business_info_crud import BusinessInfoResponse
from app.schemas.contact_info_crud import ContactInfoResponse
from app.schemas.payout_info_crud import PayoutInfoResponse
from app.schemas.shipments_info_crud import ShipmentsInfoResponse
from app.schemas.store_info_crud import StoreInfoResponse


class StoreCreate(BaseModel):
    name: Annotated[str, Field(min_length=2, examples=["My Awesome Store"])]


class StoreResponse(BaseModel):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    user_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    name: Annotated[str, Field(min_length=2, examples=["My Awesome Store"])]
    is_active: Annotated[bool, Field(examples=["true"])]
    wallet_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    wallet_transaction_id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
    created_at: Annotated[str, Field(examples=["2025-04-03"])]
    updated_at: Annotated[str, Field(examples=["2025-04-03"])]


class StoreFullDetailsResponse(StoreResponse):
    business_info: BusinessInfoResponse | None = None
    contact_info: ContactInfoResponse | None = None
    payout_info: PayoutInfoResponse | None = None
    shipment_info: ShipmentsInfoResponse | None = None
    store_info: StoreInfoResponse | None = None


class StoreUpdate(BaseModel):
    name: Annotated[
        str | None, Field(min_length=2, examples=["My Even More Awesome Store"])
    ] = None


class StoreDelete(BaseModel):
    id: Annotated[str, Field(examples=["52fecfe4-c101-4d24-9f82-8d66f145dd1d"])]
