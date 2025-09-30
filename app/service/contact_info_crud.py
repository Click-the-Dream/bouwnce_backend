from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ContactInfo, User
from app.utils.responses import response_builder
from typing import Any
from app.schemas import ContactInfoResponse

class ContactInfoCRUDService:
    
    async def create(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:
        
        user = await User.whoami(id=data.get("user_id"), user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )
        existing_contact = await ContactInfo.get_by_id(id=data.get("user_id"), db=session)
        if existing_contact:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Contact info already exists for this user.",
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
    
    async def get(self, session: AsyncSession, user_id: str) -> JSONResponse:
        user = await User.whoami(id=user_id, user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )

        contact = await ContactInfo.get_by_id(id=user_id, db=session)
        if not contact:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Contact info not found.",
            )
        contact = contact[0]
        data = ContactInfoResponse(**contact.to_dict())
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Contact info retrieved successfully.",
            data=data,
        )
    
    async def update(self, session: AsyncSession, data: dict[str, Any]) -> JSONResponse:
        user = await User.whoami(id=data.get("user_id"), user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )
        
        contact = await ContactInfo.get_by_id(id=data.get("user_id"), db=session)
        if not contact:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="Contact info not found.",
            )
        contact = contact[0]
        try:
            updated_contact = await ContactInfo.update_by_id(str(contact.id), data, session)
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

    async def delete(self, session: AsyncSession, user_id: str) -> JSONResponse:
        user = await User.whoami(id=user_id, user_type="vendor", db=session)
        if not user:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND,
                status="error",
                message="User not found or is not a vendor.",
            )

        contact = await ContactInfo.get_by_id(id=user_id, db=session)
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