from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BusinessInfo
from app.utils.responses import response_builder
from app.models import User
from typing import Any

class BusinessInfoCRUDService:
    
    async def create(self, session: AsyncSession, data: dict) -> JSONResponse:
        user_id = data.get("user_id")

        user = await User.whoami(id=user_id, user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )

        existing_business = await BusinessInfo.get_by_id(user_id=user_id, session=session)
        if existing_business:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Business info already exists for this user.",
            )
        try:
            new_business = await BusinessInfo.create(data, session)
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Business info created successfully.",
                data=new_business.to_dict(),
            )

        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating business info.",
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

        business = await BusinessInfo.get_by_id(id=user_id, session=session)
        if not business:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Business info not found.",
            )
        business = business[0]
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Business info retrieved successfully.",
            data=business.to_dict(),
        )

    async def update(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:
        
        user_id = data.get("user_id")
        
        user = await User.whoami(id=user_id, user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )

        business = await BusinessInfo.get_by_id(id=user_id, session=session)
        if not business:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Business info not found.",
            )
        business = business[0]
        try:
            updated_business = await BusinessInfo.update_by_id(str(business.id), data, session)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Business info updated successfully.",
                data=updated_business.to_dict(),
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating business info.",
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

        business = await BusinessInfo.get_by_id(id=user_id, session=session)
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