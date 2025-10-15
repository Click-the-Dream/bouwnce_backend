from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Store, StoreInfo
from app.schemas import StoreInfoResponse
from app.utils.responses import response_builder


class StoreInfoCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:

        try:
            store_info: StoreInfo | None = store.store_info
            if store_info:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Store info already exists for this store.",
                )

            data["store_id"] = store.id
            new_store = await StoreInfo.create(data, db)
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
            print("Error occured while creating store store info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating store info.",
            )

    async def get(self, store: Store) -> JSONResponse:

        try:
            store_info: StoreInfo | None = store.store_info
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
        except Exception as e:
            print("Error occured while fetching store store info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while fetching store store info",
            )

    async def update(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:
        try:
            store_info: StoreInfo | None = store.store_info
            if not store_info:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Store info not found for this store.",
                )

            updated_store = await store_info.update(db, data)
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
            print("Error occured while updating store store info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating store info.",
            )

    async def delete(self, db: AsyncSession, store: Store) -> JSONResponse:

        try:
            store_info: StoreInfo | None = store.store_info
            if not store_info:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Store info not found for this store.",
                )

            await StoreInfo.delete_permanently_by_id(id=store_info.id, db=db)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store info deleted successfully.",
            )
        except Exception as e:
            print("Error occured while deleting store store info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting store info.",
            )


store_info_service = StoreInfoCRUDService()
