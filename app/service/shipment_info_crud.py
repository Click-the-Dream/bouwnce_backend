from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ShipmentInfo, User
from app.utils.responses import response_builder
from typing import Any


class ShipmentInfoCRUDService:
    
    async def create(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:
        
        user = await User.whoami(id=data.get("user_id"), user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )
        existing_shipment = await ShipmentInfo.get_by_id(id=data.get("user_id"), db=session)
        if existing_shipment:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Shipment info already exists for this user.",
            )
        try:
            new_shipment = await ShipmentInfo.create(data, session)
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Shipment info created successfully.",
                data=new_shipment.to_dict(),
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating shipment info.",
                data=str(e),
            )
    
    async def get(self, session: AsyncSession, user_id: str) -> JSONResponse:
        user = await User.whoami(id=user_id, user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )

        shipment = await ShipmentInfo.get_by_id(id=user_id, db=session)
        if not shipment:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Shipment info not found.",
            )
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Shipment info retrieved successfully.",
            data=shipment.to_dict(),
        )
    
    async def update(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:
        user = await User.whoami(id=data.get("user_id"), user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )
        shipment = await ShipmentInfo.get_by_id(id=data.get("user_id"), db=session)
        if not shipment:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Shipment info not found.",
            )
        shipment = shipment[0]
        try:
            updated_shipment = await ShipmentInfo.update_by_id(str(shipment.id), data=data, db=session)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Shipment info updated successfully.",
                data=updated_shipment.to_dict(),
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating shipment info.",
                data=str(e),
            )
    
    async def delete(self, session: AsyncSession, user_id: str) -> JSONResponse:
        user = await User.whoami(id=user_id, user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )

        shipment = await ShipmentInfo.get_by_id(id=user_id, db=session)
        if not shipment:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Shipment info not found.",
            )
        try:
            await ShipmentInfo.delete_by_id(id=user_id, db=session)
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