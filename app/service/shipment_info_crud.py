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
        data["store_id"] = store.id
        if shipment:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Shipment info already exists for this store.",
            )
        try:
            new_shipment = await ShipmentInfo.create(data, session)
            new_shipment = new_shipment.to_dict()
            new_shipment["user_id"] = str(store.user_id)
            data = ShipmentsInfoResponse(**new_shipment)

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

        shipment = shipment.to_dict()
        shipment["user_id"] = str(store.user_id)
        data = ShipmentsInfoResponse(**shipment)
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
            updated_shipment = await shipment.update(session, data)
            updated_shipment = updated_shipment.to_dict()
            updated_shipment["user_id"] = str(store.user_id)
            data = ShipmentsInfoResponse(**updated_shipment)
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

    async def delete(self, session: AsyncSession, store) -> JSONResponse:

        store = store[0]
        shipment = store.shipment_info
        if not shipment:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Shipment info not found.",
            )
        try:
            await ShipmentInfo.delete_permanently_by_id(id=shipment.id, db=session)
            return response_builder(
                status_code=status.HTTP_200_OK,
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