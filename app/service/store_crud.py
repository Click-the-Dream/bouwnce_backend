from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Store, User
from app.utils.responses import response_builder
from typing import Any
from app.schemas import StoreResponse


class StoreCRUDService:
    
    async def create(self, session: AsyncSession, data: dict) -> JSONResponse:
        user_id = data.get("user_id")

        user = await User.whoami(id=user_id, user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )

        existing_store = await Store.filter_by(user_id=user_id, db=session)
        if existing_store:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Store already exists for this user.",
            )
        try:
            new_store = await Store.create(data, session)
            data = StoreResponse(**new_store.to_dict())
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Store created successfully.",
                data=data,
            )

        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating the store.",
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

        store = await Store.filter_by(user_id=user_id, db=session)
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found for this user.",
            )
        store = store[0]
        data = StoreResponse(**store.to_dict())
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Store retrieved successfully.",
            data=data,
        )
        
    async def update(self, session: AsyncSession, store_id: str, data: dict) -> JSONResponse:
        
        store = await Store.get_by_id(id=store_id, db=session)
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found.",
            )
        try:
            updated_store = await Store.update_by_id(id=store_id, data=data, db=session)
            data = StoreResponse(**updated_store.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store updated successfully.",
                data=data,
            )

        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating the store.",
                data=str(e),
            )
    
    async def delete(self, session: AsyncSession, store_id: str) -> JSONResponse:
        
        store = await Store.get_by_id(id=store_id, db=session)
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found.",
            )
        try:
            deleted_store = await Store.delete_by_id(id=store_id, db=session)
            data = StoreResponse(**deleted_store.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store deleted successfully.",
                data=data,
            )

        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting the store.",
                data=str(e),
            )