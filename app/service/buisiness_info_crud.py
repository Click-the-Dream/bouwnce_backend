from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BusinessInfo, Store
from app.utils.responses import response_builder
from typing import Any
from app.schemas import BusinessInfoResponse

class BusinessInfoCRUDService:
    
    async def create(self, session: AsyncSession, data: dict) -> JSONResponse:
        store_id = data.get("store_id")

        store = await Store.filter_by(id=store_id, db=session, preload=["business_info"])
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found.",
            )
        store = store[0]

        business = store.business_info
        if business:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Business info already exists for this store.",
            )
        
        try:
            new_business = await BusinessInfo.create(data, session)
            data = BusinessInfoResponse(**new_business.to_dict())
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Business info created successfully.",
                data=data,
            )

        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating business info.",
                data=str(e),
            )

    async def get(self, session: AsyncSession, store_id: str) -> JSONResponse:

        store = await Store.filter_by(id=store_id, db=session, preload=["business_info"])
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found.",
            )

        store = store[0]

        business = store.business_info
        if not business:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Business info not found for this store.",
            )
        
        data = BusinessInfoResponse(**business.to_dict())
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Business info retrieved successfully.",
            data=data,
        )

    async def update(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:

        store_id = data.get("store_id")

        store = await Store.filter_by(id=store_id, db=session, preload=["business_info"])
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found.",
            )
        store = store[0]

        business = store.business_info
        if not business:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Business info not found for this store.",
            )

        try:
            updated_business = await business.update(session, data)
            data = BusinessInfoResponse(**updated_business.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Business info updated successfully.",
                data=data,
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating business info.",
                data=str(e),
            )

    async def delete(self, session: AsyncSession, store_id: str) -> JSONResponse:

        business = await BusinessInfo.filter_by(store_id=store_id, db=session)
        if not business:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Business info not found.",
            )
        business = business[0]
        try:
            await BusinessInfo.delete_by_id(business.id, session)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Business info deleted successfully.",
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting business info.",
                data=str(e),
            )