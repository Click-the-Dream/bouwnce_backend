from typing import Any

from fastapi import APIRouter, status

from app.api.dependencies import CurrentStore, dbSessionDep
from app.schemas import (
    ShipmentsInfoCreate,
    ShipmentsInfoResponse,
    ShipmentsInfoUpdate,
    BaseResponse
)
from app.service import shipment_info_service

router = APIRouter(tags=["Shipment Information"], prefix="/shipment")


@router.post(
    "/",
    response_model=BaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create shipment information",
)
async def create_shipment_info(
    shipment_data: ShipmentsInfoCreate,
    session: dbSessionDep,
    current_store: CurrentStore,
):
    return await shipment_info_service.create(
        session, shipment_data.model_dump(), current_store
    )


@router.get(
    "",
    response_model=ShipmentsInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get shipment information by user ID",
)
async def get_shipment_info(current_store: CurrentStore):
    return await shipment_info_service.get(current_store)


@router.put(
    "/{id}",
    response_model=ShipmentsInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Update shipment information",
)
async def update_shipment_info(
    id: str,
    shipment_data: ShipmentsInfoUpdate,
    session: dbSessionDep,
    current_store: CurrentStore,
):
    return await shipment_info_service.update(
        id, session, shipment_data.model_dump(exclude_unset=True), current_store
    )


@router.delete(
    "/",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Delete shipment information",
)
async def delete_shipment_info(
    id: str, session: dbSessionDep, current_store: CurrentStore
):
    return await shipment_info_service.delete(id, session, current_store)
