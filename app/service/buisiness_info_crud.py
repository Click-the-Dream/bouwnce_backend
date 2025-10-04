from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BusinessInfo, Store
from app.utils.responses import response_builder
from typing import Any
from app.schemas import BusinessInfoResponse

class BusinessInfoCRUDService:

    async def create(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store[0]
        business = store.business_info
        data['store_id'] = store.id
        if business:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Business info already exists for this store.",
            )
        
        try:
            new_business = await BusinessInfo.create(data, session)
            new_business = new_business.to_dict()
            new_business["user_id"] = str(store.user_id)
            data = BusinessInfoResponse(**new_business)
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

    async def get(self, current_store) -> JSONResponse:

        store = current_store[0]
        business = store.business_info
        if not business:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Business info not found for this store.",
            )
        data = business.to_dict()
        data["user_id"] = str(store.user_id)
        data = BusinessInfoResponse(**data)
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Business info retrieved successfully.",
            data=data,
        )

    async def update(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store[0]
        business = store.business_info
        if not business:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Business info not found for this store.",
            )

        try:
            updated_business = await business.update(session, data)
            updated_business = updated_business.to_dict()
            updated_business["user_id"] = str(store.user_id)
            data = BusinessInfoResponse(**updated_business)
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

    async def delete(self, session: AsyncSession, store) -> JSONResponse:

        store = store[0]
        business = store.business_info
        if not business:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Business info not found for this store.",
            )
        try:
            await BusinessInfo.delete_permanently_by_id(business.id, session)
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