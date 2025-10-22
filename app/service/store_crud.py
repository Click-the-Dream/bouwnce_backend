from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Store, User
from app.models.products import product_domain
from app.schemas import (
    BusinessInfoResponse,
    ContactInfoResponse,
    PayoutInfoResponse,
    ShipmentsInfoResponse,
    StoreFullDetailsResponse,
    StoreInfoResponse,
    StoreResponse,
)
from app.models import Store, Wallet, WalletTransaction
from app.utils.responses import response_builder


class StoreCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], user: User
    ) -> JSONResponse:

        try:
            data["user_id"] = user.id
            new_store = await Store.create(data, db)
            new_store = await Store.create(data, db)
            wallet = await Wallet.create({"user_id": user.id}, db)
            await WalletTransaction.create({"wallet_id": wallet.id}, db)
            data = StoreResponse(**new_store.to_dict())
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Store created successfully.",
                data=data,
            )

        except Exception as e:
            print("Error occured while creating store: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating the store.",
            )

    async def get(self, current_store: Store) -> JSONResponse:
        try:
            data = StoreResponse(**current_store.to_dict())

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store retrieved successfully.",
                data=data,
            )
        except Exception as e:
            print("Error occured while fetching store: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while fetching store",
            )

    async def get_vendor_store(self, vendor_id: str, db: AsyncSession):
        try:
            stores = await Store.get_by({"user_id": vendor_id}, db)
            store_response = [
                StoreResponse(**store.to_dict()) for store in stores["data"]
            ]

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully fetch all stores of a vendor",
                data=store_response,
            )
        except Exception as e:
            print("Error occured while fetching vendor store: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while fetching vendor store",
            )

    async def get_full_details(self, current_store: Store) -> JSONResponse:
        try:
            store_full_response = StoreFullDetailsResponse(
                id=str(current_store.id),
                user_id=str(current_store.user_id),
                name=current_store.name,
                is_active=current_store.is_active,
                created_at=current_store.created_at.isoformat(),
                updated_at=current_store.updated_at.isoformat(),
            )

            if current_store.business_info:
                print(current_store.business_info.to_dict())
                store_full_response.business_info = BusinessInfoResponse(
                    **current_store.business_info.to_dict()
                )

            if current_store.contact_info:
                store_full_response.contact_info = ContactInfoResponse(
                    **current_store.contact_info.to_dict()
                )

            if current_store.payout_info:
                store_full_response.payout_info = PayoutInfoResponse(
                    **current_store.payout_info.to_dict()
                )

            if current_store.shipment_info:
                store_full_response.shipment_info = ShipmentsInfoResponse(
                    **current_store.shipment_info.to_dict()
                )

            if current_store.store_info:
                store_full_response.store_info = StoreInfoResponse(
                    **current_store.store_info.to_dict()
                )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="successfully fetched Store full details",
                data=store_full_response,
            )
        except Exception as e:
            print("Error occured while fetching store full details: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while fetching store full details",
            )

    async def get_stores(
        self,
        db: AsyncSession,
        name: str | None = None,
        page: int | None = 1,
        page_size: int | None = 10,
    ):
        try:
            filter = {}
            if name:
                filter["name"] = f"%{name}%"

            stores = await Store.get_by(filter, db, page, page_size)
            store_response = [
                StoreResponse(**store.to_dict()) for store in stores["data"]
            ]

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully retrived paginated stores",
                data={
                    "stores": store_response,
                    "total": stores["total"],
                    "page": stores["page"],
                    "page_size": stores["page_size"],
                },
            )
        except Exception as e:
            print("Error occured while fetching all stores data: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error fetching stores",
            )

    async def update(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:

        try:
            if not store:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Store not found.",
                )

            updated_store = await store.update(db=db, data=data)
            data = StoreResponse(**updated_store.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store updated successfully.",
                data=data,
            )

        except Exception as e:
            print("Error occured while updating store: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating the store.",
            )

    async def delete(self, db: AsyncSession, current_store: Store) -> JSONResponse:

        try:
            deleted_store = await Store.delete_permanently_by_id(
                id=str(current_store.id), db=db
            )
            data = StoreResponse(**deleted_store.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store deleted successfully.",
                data=data,
            )

        except Exception:
            print("Error occured while deleting store")
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting the store.",
            )

    async def deactivate(self, db: AsyncSession, store: Store) -> JSONResponse:

        try:
            store.is_active = False

            # Deactive all stores products
            await product_domain.deactivate_stores_products(str(store.id))

            await store.save(db)
            store_response = StoreResponse(**store.to_dict())

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store is successfully deactivated",
                data=store_response,
            )
        except Exception as e:
            print("Error occured while deactivating store: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while deactivating store",
            )

    async def activate(self, db: AsyncSession, store: Store) -> JSONResponse:

        try:
            store.is_active = True

            # Activate all stores products
            await product_domain.activate_stores_prouducts(str(store.id))

            await store.save(db)
            store_response = StoreResponse(**store.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully activate store",
                data=store_response,
            )
        except Exception as e:
            print("Error occured while activating store: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while activating store",
            )


store_service = StoreCRUDService()
