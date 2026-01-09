from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContactInfo, Store
from app.schemas import ContactInfoResponse
from app.utils.exception import (
    BadRequestException,
    InternalServerErrorException,
    NotFoundException,
)
from app.utils.responses import response_builder


class ContactInfoCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> ContactInfoResponse:
        try:
            contact: ContactInfo | None = store.contact_info
            if contact:
                raise BadRequestException(
                    message="Contact info already exists for this store."
                )

            data["store_id"] = store.id
            new_contact = await ContactInfo.create(data, db)
            new_contact = new_contact.to_dict()
            new_contact["user_id"] = str(store.user_id)

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Contact info created successfully.",
                data=new_contact,
            )
        except Exception as e:
            print("Error occured while creating contact info: ", str(e))
            raise InternalServerErrorException(
                message="An error occurred while creating contact info."
            ) from None

    async def get(self, store: Store) -> ContactInfoResponse:
        try:
            contact: ContactInfo | None = store.contact_info
            if not contact:
                raise NotFoundException(message="Contact info not found.")

            contact = contact.to_dict()
            contact["user_id"] = str(store.user_id)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Contact info retrieved successfully.",
                data=contact,
            )
        except Exception as e:
            print("Error occured while fetching store contact info: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while fetching store contact info"
            ) from None

    async def update(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> ContactInfoResponse:
        try:
            contact: ContactInfo | None = store.contact_info

            if not contact:
                raise NotFoundException(message="Contact info not found.")

            updated_contact = await contact.update(db, data)
            updated_contact = updated_contact.to_dict()
            updated_contact["user_id"] = str(store.user_id)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Contact info updated successfully.",
                data=updated_contact,
            )
        except Exception as e:
            print("Error occured while updating contact info: ", str(e))
            raise InternalServerErrorException(
                message="An error occurred while updating contact info."
            ) from None

    async def delete(self, session: AsyncSession, store: Store) -> dict[str, Any]:

        try:
            contact: ContactInfo | None = store.contact_info
            if not contact:
                raise NotFoundException(
                    message="Contact info not found for this store."
                )

            await ContactInfo.delete_permanently_by_id(str(contact.id), session)
            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Contact info deleted successfully.",
            )
        except Exception as e:
            print("Error deleting store contact info: ", str(e))
            raise InternalServerErrorException(
                message="An error occurred while deleting contact info."
            ) from None


contact_info_service = ContactInfoCRUDService()
