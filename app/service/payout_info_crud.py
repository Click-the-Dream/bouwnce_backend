from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import PayoutInfo, Store
from app.utils.responses import response_builder
from typing import Any
from app.schemas import PayoutInfoResponse

class PayoutInfoCRUDService:

    async def create(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:

        store = await Store.filter_by(id=data.get("store_id"), db=session, preload=["payout_info"])
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found.",
            )
        store = store[0]
        payout = store.payout_info
        if payout:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Payout info already exists for this store.",
            )
        try:
            new_payout = await PayoutInfo.create(data, session)
            data = PayoutInfoResponse(**new_payout.to_dict())
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
    
    async def get(self, session: AsyncSession, store_id: str) -> JSONResponse:

        store = await Store.filter_by(id=store_id, db=session, preload=["payout_info"])
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found.",
            )
        store = store[0]
        payout = store.payout_info
        if not payout:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Payout info not found.",
            )
        data = PayoutInfoResponse(**payout.to_dict())
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Payout info retrieved successfully.",
            data=data,
        )
    
    async def update(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:
        
        store = await Store.filter_by(id=data.get("store_id"), db=session, preload=["payout_info"])
        if not store:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Store not found.",
            )
        store = store[0]
        payout = store.payout_info
        if not payout:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Payout info not found.",
            )
        try:
            updated_payout = await payout.update(data, session)
            data = PayoutInfoResponse(**updated_payout.to_dict())
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
    
    async def delete(self, session: AsyncSession, store_id: str) -> JSONResponse:
        
        payout = await PayoutInfo.filter_by(id=store_id, db=session)
        if not payout:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Payout info not found.",
            )
        payout = payout[0]
        try:
            await PayoutInfo.delete_by_id(id=payout.id, db=session)
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
