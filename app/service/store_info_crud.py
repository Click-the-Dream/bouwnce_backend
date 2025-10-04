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
        data["store_id"] = store.id
        if store_info:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Store info already exists for this store.",
            )

        try:
            new_store = await StoreInfo.create(data, session)
            new_store = new_store.to_dict()
            new_store["user_id"] = str(store.user_id)
            data = StoreInfoResponse(**new_store)
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
        store_info = store_info.to_dict()
        store_info["user_id"] = str(store.user_id)
        data = StoreInfoResponse(**store_info)
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
            updated_store = await store_info.update(session, data)
            updated_store = updated_store.to_dict()
            updated_store["user_id"] = str(store.user_id)
            data = StoreInfoResponse(**updated_store)
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

    async def delete(self, session: AsyncSession, store) -> JSONResponse:

        try:
            store = store[0]
            store_info = store.store_info
            if not store_info:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Store info not found for this store.",
                )
            await StoreInfo.delete_permanently_by_id(id=store_info.id, db=session)
            return response_builder(
                status_code=status.HTTP_200_OK,
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