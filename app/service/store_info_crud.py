from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import StoreInfo, Store
from app.utils.responses import response_builder
from typing import Any
from app.schemas import StoreInfoResponse


class StoreInfoCRUDService:
    
    async def create(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store[0]
        store_info = store.store_info
        if store_info:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Store info already exists for this store.",
            )

        try:
            new_store = await StoreInfo.create(data, session)
            data = StoreInfoResponse(**new_store.to_dict())
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Store info created successfully.",
                data=data,
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating store info.",
                data=str(e),
            )

    async def get(self, current_store) -> JSONResponse:

        store = current_store[0]
        store_info = store.store_info
        if not store_info:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store info not found.",
            )
        data = StoreInfoResponse(**store_info.to_dict())
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Store info retrieved successfully.",
            data=data,
        )

    async def update(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store[0]
        store_info = store.store_info

        if not store_info:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store info not found for this store.",
            )
        try:
            updated_store = await store_info.update(data, session)
            data = StoreInfoResponse(**updated_store.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store info updated successfully.",
                data=data,
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating store info.",
                data=str(e),
            )

    async def delete(self, session: AsyncSession, store_id: str) -> JSONResponse:
        
        store = await Store.filter_by(id=store_id, db=session)
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store info not found.",
            )
        store = store[0]
        try:
            await StoreInfo.delete_by_id(id=store.id, db=session)
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