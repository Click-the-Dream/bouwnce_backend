from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessInfo, Store, User
from app.schemas import BusinessInfoResponse
from app.utils.responses import response_builder


class BusinessInfoCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], current_vendor: User
    ) -> JSONResponse:
        try:
            # Automatically create a store if not exist
            store = await Store.filter_by(
                filter={"user_id": str(current_vendor.id)},
                db=db,
                preload=["business_info"],
            )
            if len(store) == 0:
                store = await Store.create(
                    data={"user_id": current_vendor.id, "name": data["name"]}, db=db
                )
            else:
                store = store[0]

            business: BusinessInfo | None = store.business_info
            if business:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Business info already exists for this store.",
                )

            data["store_id"] = store.id
            new_business = await BusinessInfo.create(data, db)
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
            print("Error occured while creating business info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating business info.",
            )

    async def get(self, store: Store) -> JSONResponse:
        try:
            business: BusinessInfo | None = store.business_info
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
        except Exception as e:
            print("Error occured while fetching business info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while fetching business info",
            )

    async def update(
        self, db: AsyncSession, data: dict[str, Any], current_store: Store
    ) -> JSONResponse:
        try:
            business: BusinessInfo | None = current_store.business_info
            if not business:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Business info not found for this store.",
                )

            # Automatically update store name
            if data.get("name"):
                await current_store.update(db=db, data={"name": data["name"]})

            updated_business = await business.update(db=db, data=data)
            updated_business = updated_business.to_dict()
            updated_business["user_id"] = str(current_store.user_id)
            data = BusinessInfoResponse(**updated_business)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Business info updated successfully.",
                data=data,
            )
        except Exception as e:
            print("Error occured while updating business info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating business info.",
            )

    async def delete(self, db: AsyncSession, store: Store) -> JSONResponse:
        try:
            business: BusinessInfo | None = store.business_info
            if not business:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Business info not found for this store.",
                )

            await BusinessInfo.delete_permanently_by_id(business.id, db)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Business info deleted successfully.",
            )
        except Exception as e:
            print("Error occured while deleting buisness info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting business info.",
            )


business_service = BusinessInfoCRUDService()
