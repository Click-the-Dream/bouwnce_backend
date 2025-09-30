from fastapi import APIRouter, Depends, status
from app.schemas import (
    ContactInfoCreate,
    ContactInfoUpdate,
    ContactInfoResponse
)
from app.service import ContactInfoCRUDService
from app.db.postgres_db_conn import get_async_session
from typing import Any


router = APIRouter(tags=["Contact Information"], prefix="/contact")

@router.post(
    "/", response_model=ContactInfoResponse, status_code=status.HTTP_201_CREATED,
    summary="Create contact information"
)
async def create_contact_info(contact_data: ContactInfoCreate, session=Depends(get_async_session)):
    return await ContactInfoCRUDService().create(session, contact_data.dict())

@router.get(
    "/{user_id}", response_model=ContactInfoResponse, status_code=status.HTTP_200_OK,
    summary="Get contact information by user ID"
)
async def get_contact_info(user_id: str, session=Depends(get_async_session)):
    return await ContactInfoCRUDService().get(session, user_id)

@router.put(
    "/", response_model=ContactInfoResponse, status_code=status.HTTP_200_OK,
    summary="Update contact information"
)
async def update_contact_info(contact_data: ContactInfoUpdate, session=Depends(get_async_session)):
    return await ContactInfoCRUDService().update(session, contact_data.dict())

@router.delete(
    "/", response_model=dict[str, Any], status_code=status.HTTP_200_OK,
    summary="Delete contact information"
)
async def delete_contact_info(user_id: str, session=Depends(get_async_session)):
    return await ContactInfoCRUDService().delete(session, user_id)  