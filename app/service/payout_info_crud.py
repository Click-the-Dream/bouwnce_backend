from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import PayoutInfo, Store
from app.utils.responses import response_builder
from typing import Any
from app.schemas import PayoutInfoResponse

class PayoutInfoCRUDService:

    async def create(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store[0]
        payout = store.payout_info
        data['store_id'] = store.id
        if payout:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Payout info already exists for this store.",
            )
        try:
            new_payout = await PayoutInfo.create(data, session)
            new_payout = new_payout.to_dict()
            new_payout["user_id"] = str(store.user_id)
            data = PayoutInfoResponse(**new_payout)
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Payout info created successfully.",
                data=data,
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating payout info.",
                data=str(e),
            )

    async def get(self, current_store) -> JSONResponse:

        store = current_store[0]
        payout = store.payout_info
        if not payout:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Payout info not found.",
            )
        payout = payout.to_dict()
        payout["user_id"] = str(store.user_id)
        data = PayoutInfoResponse(**payout)
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Payout info retrieved successfully.",
            data=data,
        )

    async def update(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store[0]
        payout = store.payout_info
        if not payout:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Payout info not found.",
            )
        try:
            updated_payout = await payout.update(session, data)
            updated_payout = updated_payout.to_dict()
            updated_payout["user_id"] = str(store.user_id)
            data = PayoutInfoResponse(**updated_payout)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Payout info updated successfully.",
                data=data,
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating payout info.",
                data=str(e),
            )

    async def delete(self, session: AsyncSession, store) -> JSONResponse:

        store = store[0]
        payout = store.payout_info
        if not payout:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Payout info not found for this store.",
            )
        try:
            await PayoutInfo.delete_permanently_by_id(payout.id, session)
            return response_builder(
                status_code=status.HTTP_200_OK,
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
