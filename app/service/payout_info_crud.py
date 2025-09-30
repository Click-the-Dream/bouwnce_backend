from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import PayoutInfo, User
from app.utils.responses import response_builder
from typing import Any


class PayoutInfoCRUDService:

    async def create(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:

        user = await User.whoami(id=data.get("user_id"), user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )
        existing_payout = await PayoutInfo.get_by_id(id=data.get("user_id"), db=session)
        if existing_payout:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Payout info already exists for this user.",
            )
        try:
            new_payout = await PayoutInfo.create(data, session)
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Payout info created successfully.",
                data=new_payout.to_dict(),
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating payout info.",
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

        payout = await PayoutInfo.get_by_id(id=user_id, db=session)
        if not payout:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Payout info not found.",
            )
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Payout info retrieved successfully.",
            data=payout.to_dict(),
        )
    
    async def update(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:
        user = await User.whoami(id=data.get("user_id"), user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )

        payout = await PayoutInfo.get_by_id(id=data.get("user_id"), db=session)
        if not payout:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Payout info not found.",
            )
        payout = payout[0]
        try:
            updated_payout = await PayoutInfo.update_by_id(str(payout.id), data=data, db=session)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Payout info updated successfully.",
                data=updated_payout.to_dict(),
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating payout info.",
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

        payout = await PayoutInfo.get_by_id(id=user_id, db=session)
        if not payout:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Payout info not found.",
            )
        try:
            await PayoutInfo.delete_by_id(id=user_id, db=session)
            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Payout info deleted successfully.",
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting payout info.",
                data=str(e),
            )
