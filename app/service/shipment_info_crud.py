from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ShipmentInfo, Store
from app.utils.responses import response_builder
from typing import Any
from app.schemas import ShipmentsInfoResponse

class ShipmentInfoCRUDService:
    
    async def create(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store[0]
        shipment = store.shipment_info
        if shipment:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Shipment info already exists for this store.",
            )
        try:
            new_shipment = await ShipmentInfo.create(data, session)
            data = ShipmentsInfoResponse(**new_shipment.to_dict())
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Shipment info created successfully.",
                data=data,
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating shipment info.",
                data=str(e),
            )

    async def get(self, current_store) -> JSONResponse:

        store = current_store[0]
        shipment = store.shipment_info
        if not shipment:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Shipment info not found.",
            )

        data = ShipmentsInfoResponse(**shipment.to_dict())
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Shipment info retrieved successfully.",
            data=data,
        )

    async def update(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store[0]
        shipment = store.shipment_info
        if not shipment:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Shipment info not found.",
            )
        try:
            updated_shipment = await shipment.update(data, session)
            data = ShipmentsInfoResponse(**updated_shipment.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Shipment info updated successfully.",
                data=data,
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating shipment info.",
                data=str(e),
            )

    async def delete(self, session: AsyncSession, store_id: str) -> JSONResponse:

        shipment = await ShipmentInfo.filter_by(store_id=store_id, db=session)
        if not shipment:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Shipment info not found.",
            )
        shipment = shipment[0]
        try:
            await ShipmentInfo.delete_by_id(id=shipment.id, db=session)
            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Shipment info deleted successfully.",
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting shipment info.",
                data=str(e),
            )