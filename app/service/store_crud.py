from typing import Any

from fastapi import UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Store, User, Wallet
from app.models.products import product_domain
from app.utils.cloudinary_utils import (
    cleanup_temp_files,
    delete_images,
    save_uploaded_file_temp,
    upload_image,
)
from app.utils.exception import (
    BadRequestException,
    ConflictException,
    InternalServerErrorException,
    NotFoundException,
)
from app.utils.helper import is_valid_uuid
from app.utils.responses import response_builder


class StoreCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], user: User
    ) -> dict[str, Any]:

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

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Store created successfully.",
                data=new_store.to_dict(),
            )

        except Exception as e:
            print("Error occured while creating store: ", str(e))
            raise InternalServerErrorException(
                message="An error occurred while creating the store."
            ) from None

    async def get(self, current_store: Store) -> dict[str, Any]:
        try:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store retrieved successfully.",
                data=current_store.to_dict(),
            )
        except Exception as e:
            print("Error occured while fetching store: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while fetching store"
            ) from None

    async def get_vendor_store(self, vendor_id: str, db: AsyncSession):
        try:
            print("Vendor ID: ", vendor_id)
            if not is_valid_uuid(vendor_id):
                raise NotFoundException(message="Invalid vendor id")

            stores = await Store.get_by(filter={"user_id": vendor_id}, db=db, all=True)
            store_response = [store.to_dict() for store in stores["data"]]

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully fetch all stores of a vendor",
                data=store_response,
            )
        except Exception as e:
            print("Error occured while fetching vendor store: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while fetching vendor store"
            ) from None

    async def get_full_details(self, current_store: Store) -> dict[str, Any]:
        try:
            store_full_response = {
                "id": str(current_store.id),
                "user_id": str(current_store.user_id),
                "name": current_store.name,
                "address": current_store.address,
                "phone_number": current_store.phone_number,
                "email": current_store.email,
                "store_description": current_store.store_description,
                "store_logo": current_store.store_logo,
                "store_banner": current_store.store_banner,
                "is_active": current_store.is_active,
                "created_at": current_store.created_at.isoformat(),
                "updated_at": current_store.updated_at.isoformat(),
            }

            if current_store.contact_info:
                store_full_response["contact_info"] = (
                    current_store.contact_info.to_dict()
                )

            if current_store.payout_info:
                store_full_response["payout_info"] = current_store.payout_info.to_dict()

            if current_store.shipment_info:
                store_full_response["shipment_info"] = [
                    shipment_info.to_dict()
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
            raise InternalServerErrorException(
                message="Error occured while fetching store full details"
            ) from None

    async def get_store_onboarding_status(self, store: Store) -> dict[str, Any]:
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
                data={
                    "is_onboarded": is_onboarded,
                    "missing_sections": missing_sections,
                },
            )
        except Exception as e:
            print("Error occured while fetching store onboarding status: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while fetching store onboarding status"
            ) from None

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
            store_response = [store.to_dict() for store in stores["data"]]

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
            raise InternalServerErrorException(
                message="Error fetching stores"
            ) from None

    async def update(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> dict[str, Any]:

        try:
            if not store:
                raise NotFoundException(message="Store not found.")

            updated_store = await store.update(db=db, data=data)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store updated successfully.",
                data=updated_store.to_dict(),
            )

        except Exception as e:
            print("Error occured while updating store: ", str(e))
            raise InternalServerErrorException(
                message="An error occurred while updating the store."
            ) from None

    async def update_store_branding(
        self,
        store: Store,
        db: AsyncSession,
        store_description: str | None = None,
        store_logo: UploadFile | None = None,
        store_banner: UploadFile | None = None,
    ) -> dict[str, Any]:
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

                except Exception:
                    raise InternalServerErrorException("Something went wrong") from None
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
                except Exception:
                    raise InternalServerErrorException(
                        "Error occured while uplaoding store banner/logo."
                    ) from None
                finally:
                    await cleanup_temp_files(path)

            await store.update(db=db, data=data)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully update Store branding",
                data=store.to_dict(),
            )
        except Exception as e:
            print("Error update store branding: ", str(e))
            raise InternalServerErrorException(
                "error occured while updating store branding."
            ) from None

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
                    raise BadRequestException(
                        message="Unable to delete store brand images"
                    )

            raise ConflictException(message="Nothing to delete")

        except Exception as e:
            print("Error delete store brand images: ", str(e))
            raise InternalServerErrorException(
                "Error occured while deleting store brand images"
            ) from None

    async def delete(self, db: AsyncSession, current_store: Store) -> dict[str, Any]:

        try:
            await Store.delete_permanently_by_id(id=str(current_store.id), db=db)

            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Store deleted successfully.",
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None

        except Exception:
            print("Error occured while deleting store")
            raise InternalServerErrorException(
                message="An error occurred while deleting the store."
            ) from None

    async def deactivate(self, db: AsyncSession, store: Store) -> dict[str, Any]:

        try:
            store.is_active = False

            # Deactive all stores products
            await product_domain.deactivate_stores_products(str(store.id))

            await store.save(db)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Store is successfully deactivated",
            )
        except Exception as e:
            print("Error occured while deactivating store: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while deactivating store"
            ) from None

    async def activate(self, db: AsyncSession, store: Store) -> dict[str, Any]:

        try:
            store.is_active = True

            # Activate all stores products
            await product_domain.activate_stores_prouducts(str(store.id))

            await store.save(db)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully activate store",
            )
        except Exception as e:
            print("Error occured while activating store: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while activating store"
            ) from None


store_service = StoreCRUDService()
