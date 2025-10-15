from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContactInfo, Store
from app.schemas import ContactInfoResponse
from app.utils.responses import response_builder


class ContactInfoCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:
        try:
            contact: ContactInfo | None = store.contact_info
            if contact:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Contact info already exists for this store.",
                )

            data["store_id"] = store.id
            new_contact = await ContactInfo.create(data, db)
            new_contact = new_contact.to_dict()
            new_contact["user_id"] = str(store.user_id)
            data = ContactInfoResponse(**new_contact)
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Contact info created successfully.",
                data=data,
            )
        except Exception as e:
            print("Error occured while creating contact info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating contact info.",
            )

    async def get(self, store: Store) -> JSONResponse:
        try:
            contact: ContactInfo | None = store.contact_info
            if not contact:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Contact info not found.",
                )
            contact = contact.to_dict()
            contact["user_id"] = str(store.user_id)
            data = ContactInfoResponse(**contact)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Contact info retrieved successfully.",
                data=data,
            )
        except Exception as e:
            print("Error occured while fetching store contact info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while fetching store contact info",
            )

    async def update(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> JSONResponse:
        try:
            contact: ContactInfo | None = store.contact_info

            if not contact:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Contact info not found.",
                )

            updated_contact = await contact.update(db, data)
            updated_contact = updated_contact.to_dict()
            updated_contact["user_id"] = str(store.user_id)
            data = ContactInfoResponse(**updated_contact)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Contact info updated successfully.",
                data=data,
            )
        except Exception as e:
            print("Error occured while updating contact info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating contact info.",
            )

    async def delete(self, session: AsyncSession, store: Store) -> JSONResponse:

        try:
            contact: ContactInfo | None = store.contact_info
            if not contact:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Contact info not found for this store.",
                )

            await ContactInfo.delete_permanently_by_id(str(contact.id), session)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Contact info deleted successfully.",
            )
        except Exception as e:
            print("Error deleting store contact info: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting contact info.",
            )


contact_info_service = ContactInfoCRUDService()
