from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Store, User
from app.utils.responses import response_builder
from typing import Any
from app.schemas import StoreResponse


class StoreCRUDService:

    async def create(self, session: AsyncSession, data: dict[str, Any], user) -> JSONResponse:
        
        try:
            data["user_id"] = user.id
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

    async def get(self, current_store) -> JSONResponse:

        data = StoreResponse(**current_store.to_dict())

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Store retrieved successfully.",
            data=data,
        )
    
    async def update(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found.",
            )
        try:
            updated_store = await store.update(db=session, data=data)
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

    async def delete(self, session: AsyncSession, current_store) -> JSONResponse:

        try:
            deleted_store = await Store.delete_permanently_by_id(id=str(current_store.id), db=session)
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