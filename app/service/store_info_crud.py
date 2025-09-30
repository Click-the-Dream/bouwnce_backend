from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import StoreInfo, User
from app.utils.responses import response_builder
from typing import Any

class StoreInfoCRUDService:
    
    async def create(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:
        
        user = await User.whoami(id=data.get("user_id"), user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )
        existing_store = await StoreInfo.get_by_id(id=data.get("user_id"), db=session)
        if existing_store:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Store info already exists for this user.",
            )
        try:
            new_store = await StoreInfo.create(data, session)
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Store info created successfully.",
                data=new_store.to_dict(),
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating store info.",
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

        store = await StoreInfo.get_by_id(id=user_id, db=session)
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store info not found.",
            )
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Store info retrieved successfully.",
            data=store.to_dict(),
        )

    async def update(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:
        user = await User.whoami(id=data.get("user_id"), user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )

        store = await StoreInfo.get_by_id(id=data.get("user_id"), db=session)
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store info not found.",
            )
        store = store[0]
        try:
            updated_store = await StoreInfo.update_by_id(str(store.id), data=data, db=session)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store info updated successfully.",
                data=updated_store.to_dict(),
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating store info.",
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

        store = await StoreInfo.get_by_id(id=user_id, db=session)
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store info not found.",
            )

        try:
            await StoreInfo.delete_by_id(id=user_id, db=session)
            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Store info deleted successfully.",
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting store info.",
                data=str(e),
            )