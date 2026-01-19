from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContactInfo, Store
from app.schemas import ContactInfoResponse
from app.utils.exception import (
    BadRequestException,
    NotFoundException,
)
from app.utils.responses import response_builder


class ContactInfoCRUDService:

    async def create(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> ContactInfoResponse:

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

    async def get(self, store: Store) -> ContactInfoResponse:

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

    async def update(
        self, db: AsyncSession, data: dict[str, Any], store: Store
    ) -> ContactInfoResponse:

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

    async def delete(self, session: AsyncSession, store: Store) -> dict[str, Any]:

        contact: ContactInfo | None = store.contact_info
        if not contact:
            raise NotFoundException(message="Contact info not found for this store.")

        await ContactInfo.delete_permanently_by_id(str(contact.id), session)
        return response_builder(
            status_code=status.HTTP_204_NO_CONTENT,
            status="success",
            message="Contact info deleted successfully.",
        )


contact_info_service = ContactInfoCRUDService()
