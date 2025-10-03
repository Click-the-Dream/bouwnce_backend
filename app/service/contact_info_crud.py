from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ContactInfo, Store
from app.utils.responses import response_builder
from typing import Any
from app.schemas import ContactInfoResponse

class ContactInfoCRUDService:

    async def create(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:

        store = current_store[0]
        contact = store.contact_info
        if contact:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Contact info already exists for this store.",
            )
        try:
            new_contact = await ContactInfo.create(data, session)
            data = ContactInfoResponse(**new_contact.to_dict())
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Contact info created successfully.",
                data=data,
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while creating contact info.",
                data=str(e),
            )

    async def get(self, current_store) -> JSONResponse:
        store = current_store[0]
    
        contact = store.contact_info
        if not contact:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Contact info not found.",
            )
        data = ContactInfoResponse(**contact.to_dict())
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Contact info retrieved successfully.",
            data=data,
        )
    
    async def update(self, session: AsyncSession, data: dict[str, Any], current_store) -> JSONResponse:
        store = current_store[0]
        contact = store.contact_info
   
        if not contact:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Contact info not found.",
            )
        try:
            updated_contact = await contact.update(data, session)
            data = ContactInfoResponse(**updated_contact.to_dict())
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Contact info updated successfully.",
                data=data,
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while updating contact info.",
                data=str(e),
            )

    async def delete(self, session: AsyncSession, store_id: str) -> JSONResponse:
        
        contact = await ContactInfo.filter_by(store_id=store_id, db=session)
        if not contact:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Contact info not found.",
            )
        contact = contact[0]
        try:
            await ContactInfo.delete_by_id(str(contact.id), session)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Contact info deleted successfully.",
            )
        except Exception as e:
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="An error occurred while deleting contact info.",
                data=str(e),
            )