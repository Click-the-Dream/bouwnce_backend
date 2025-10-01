from fastapi import APIRouter, Depends, status
from app.schemas import (
    ShipmentsInfoCreate,
    ShipmentsInfoUpdate,
    ShipmentsInfoResponse,
)
from app.service import ShipmentInfoCRUDService
from app.api.dependencies import dbSessionDep
from typing import Any


router = APIRouter(tags=["Shipment Information"], prefix="/shipment")


@router.post(
    "/", response_model=ShipmentsInfoResponse, status_code=status.HTTP_201_CREATED,
    summary="Create shipment information"
)
async def create_shipment_info(shipment_data: ShipmentsInfoCreate, session: dbSessionDep):
    return await ShipmentInfoCRUDService().create(session, shipment_data.dict())

@router.get(
    "/{user_id}", response_model=ShipmentsInfoResponse, status_code=status.HTTP_200_OK,
    summary="Get shipment information by user ID"
)
async def get_shipment_info(user_id: str, session: dbSessionDep):
    return await ShipmentInfoCRUDService().get(session, user_id)

@router.put(
    "/", response_model=ShipmentsInfoResponse, status_code=status.HTTP_200_OK,
    summary="Update shipment information"
)
async def update_shipment_info(shipment_data: ShipmentsInfoUpdate, session: dbSessionDep):
    return await ShipmentInfoCRUDService().update(session, shipment_data.dict())

@router.delete(
    "/", response_model=dict[str, Any], status_code=status.HTTP_200_OK,
    summary="Delete shipment information"
)
async def delete_shipment_info(user_id: str, session: dbSessionDep):
    return await ShipmentInfoCRUDService().delete(session, user_id)