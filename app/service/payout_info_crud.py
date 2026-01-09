from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PayoutInfo, Store
from app.utils.exception import (
    BadRequestException,
    InternalServerErrorException,
    NotFoundException,
)
from app.utils.responses import response_builder


class PayoutInfoCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> dict[str, Any]:

        try:
            payout: PayoutInfo | None = store.payout_info
            if payout:
                raise BadRequestException(
                    message="Payout info already exists for this store."
                )

            data["store_id"] = store.id
            new_payout = await PayoutInfo.create(data, db)
            new_payout = new_payout.to_dict()

            new_payout["user_id"] = str(store.user_id)

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Payout info created successfully.",
                data=new_payout,
            )
        except Exception as e:
            print("Error creating store contact info: ", str(e))
            raise InternalServerErrorException(
                message="An error occurred while creating payout info."
            ) from None

    async def get(self, store: Store) -> dict[str, Any]:

        try:
            payout: PayoutInfo | None = store.payout_info
            if not payout:
                raise NotFoundException(message="Payout info not found.")

            payout = payout.to_dict()
            payout["user_id"] = str(store.user_id)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Payout info retrieved successfully.",
                data=payout,
            )
        except Exception as e:
            print("Error fetching store payout info: ", str(e))
            raise InternalServerErrorException(
                message="Error fetching store payout info"
            ) from None

    async def update(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> dict[str, Any]:
        try:
            payout: PayoutInfo | None = store.payout_info
            if not payout:
                raise NotFoundException(message="Payout info not found.")

            updated_payout = await payout.update(db, data)
            updated_payout = updated_payout.to_dict()
            updated_payout["user_id"] = str(store.user_id)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Payout info updated successfully.",
                data=updated_payout,
            )
        except Exception as e:
            print("Error occured while updating store payout info: ", str(e))
            raise InternalServerErrorException(
                message="An error occurred while updating payout info."
            ) from None

    async def delete(self, db: AsyncSession, store: Store) -> dict[str, Any]:
        try:
            payout: PayoutInfo | None = store.payout_info
            if not payout:
                raise NotFoundException(message="Payout info not found for this store.")

            await PayoutInfo.delete_permanently_by_id(payout.id, db)
            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Payout info deleted successfully.",
            )
        except Exception as e:
            print("Error occured while deleting store payout info: ", str(e))
            raise InternalServerErrorException(
                message="An error occurred while deleting payout info."
            ) from None


payout_info_service = PayoutInfoCRUDService()
