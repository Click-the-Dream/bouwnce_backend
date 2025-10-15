from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PayoutInfo, Store
from app.schemas import PayoutInfoResponse
from app.utils.responses import response_builder


class PayoutInfoCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:

        try:
            payout: PayoutInfo | None = store.payout_info
            if payout:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Payout info already exists for this store.",
                )

            data["store_id"] = store.id
            new_payout = await PayoutInfo.create(data, db)
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
            print("Error creating store contact info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating payout info.",
            )

    async def get(self, store: Store) -> JSONResponse:

        try:
            payout: PayoutInfo | None = store.payout_info
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
        except Exception as e:
            print("Error fetching store payout info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error fetching store payout info",
            )

    async def update(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:
        try:
            payout: PayoutInfo | None = store.payout_info
            if not payout:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Payout info not found.",
                )

            updated_payout = await payout.update(db, data)
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
            print("Error occured while updating store payout info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating payout info.",
            )

    async def delete(self, db: AsyncSession, store: Store) -> JSONResponse:
        try:
            payout: PayoutInfo | None = store.payout_info
            if not payout:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Payout info not found for this store.",
                )

            await PayoutInfo.delete_permanently_by_id(payout.id, db)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Payout info deleted successfully.",
            )
        except Exception as e:
            print("Error occured while deleting store payout info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting payout info.",
            )


payout_info_service = PayoutInfoCRUDService()
