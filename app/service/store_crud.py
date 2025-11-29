from typing import Any

from fastapi import UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Store, User, Wallet
from app.models.products import product_domain
from app.schemas import (
    ContactInfoResponse,
    PayoutInfoResponse,
    ShipmentsInfoResponse,
    StoreFullDetailsResponse,
    StoreResponse,
)
from app.utils.cloudinary_utils import (
    cleanup_temp_files,
    delete_images,
    save_uploaded_file_temp,
    upload_image,
)
from app.utils.helper import is_valid_uuid
from app.utils.responses import response_builder


class StoreCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], user: User
    ) -> JSONResponse:

        try:
            store = await Store.get_by_name(data["name"].lower(), db)
            if store:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Store with name already exist",
                )

            data["user_id"] = user.id
            data["name"] = data["name"].lower()
            new_store = await Store.create(data, db)

            user.is_store_owner = True
            await user.save(db)

            await Wallet.create({"store_id": new_store.id}, db)

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
            if not is_valid_uuid(vendor_id):
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Invalid vendor id",
                )

            stores = await Store.get_by(filter={"user_id": vendor_id}, db=db)
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
                address=current_store.address,
                phone_number=current_store.phone_number,
                email=current_store.email,
                store_description=current_store.store_description,
                store_logo=current_store.store_logo,
                store_banner=current_store.store_banner,
                is_active=current_store.is_active,
                created_at=current_store.created_at.isoformat(),
                updated_at=current_store.updated_at.isoformat(),
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
                store_full_response.shipment_info = [
                    ShipmentsInfoResponse(**shipment_info.to_dict())
                    for shipment_info in current_store.shipment_info
                ]

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

    async def get_store_onboarding_status(self, store: Store) -> JSONResponse:
        try:
            missing_sections = []

            if not store.shipment_info or len(store.shipment_info) == 0:
                missing_sections.append("shipment_info")

            if not store.contact_info:
                missing_sections.append("contact_info")

            if not store.payout_info:
                missing_sections.append("payout_info")

            is_onboarded = len(missing_sections) == 0

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="sucess",
                message="Status fetched successfully",
                data={"is_onboarded": is_onboarded, "missing_sections": []},
            )
        except Exception as e:
            print("Error occured while fetching store onboarding status: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while fetching store onboarding status",
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

    async def update_store_branding(
        self,
        store: Store,
        db: AsyncSession,
        store_description: str | None = None,
        store_logo: UploadFile | None = None,
        store_banner: UploadFile | None = None,
    ) -> JSONResponse:
        try:
            data = {}
            if store_description:
                data["store_description"] = store_description

            if store_logo:
                try:
                    path = await save_uploaded_file_temp([store_logo])
                    image_result = await upload_image(path[0], str(store.id))
                    data["store_logo"] = image_result

                    # # If store has a logo already, delete it after updating is sucessful
                    if store.store_logo:
                        previous_image_id = store.store_logo["public_id"]
                        delete_images([previous_image_id])

                except Exception as e:
                    raise Exception("Something went wrong: ", str(e)) from None
                finally:
                    await cleanup_temp_files(path)

            if store_banner:
                try:
                    path = await save_uploaded_file_temp([store_banner])
                    image_result = await upload_image(path[0], str(store.id))
                    data["store_banner"] = image_result

                    # If store has banner already, delete it after updating is successfull
                    if store.store_banner:
                        previous_image_id = store.store_banner["public_id"]
                        delete_images([previous_image_id])
                except Exception as e:
                    raise Exception("Something went wrong: ", str(e)) from None
                finally:
                    await cleanup_temp_files(path)

            await store.update(db=db, data=data)

            store_response = StoreResponse(**store.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully update Store branding",
                data=store_response,
            )
        except Exception as e:
            print("Error update store branding: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Internal Server Error",
            )

    async def delete_brand_images(
        self,
        db: AsyncSession,
        store: Store,
        store_logo: bool | None = None,
        store_banner: bool | None = None,
    ):
        try:
            public_ids = []

            if store_logo is not None and store.store_logo:
                public_ids.append(store.store_logo["public_id"])

            if store_banner is not None and store.store_banner:
                public_ids.append(store.store_banner["public_id"])

            if public_ids:
                is_deleted = delete_images(public_ids)
                if is_deleted:
                    if store_logo:
                        store.store_logo = None

                    if store_banner:
                        store.store_banner = None

                    store.save(db)
                    return response_builder(
                        status_code=status.HTTP_204_NO_CONTENT,
                        status="success",
                        message="Store branding image successfully deleted",
                    )
                else:
                    return response_builder(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        status="error",
                        message="Unable to delete store brand images",
                    )

            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Nothing to delete",
            )

        except Exception as e:
            print("Error delete store brand images: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Internal server error",
            )

    async def delete(self, db: AsyncSession, current_store: Store) -> JSONResponse:

        try:
            deleted_store = await Store.delete_permanently_by_id(
                id=str(current_store.id), db=db
            )
            data = StoreResponse(**deleted_store.to_dict())
            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
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
