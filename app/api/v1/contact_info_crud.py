from typing import Any

from fastapi import APIRouter, status

from app.api.dependencies import CurrentStore, dbSessionDep
from app.schemas import ContactInfoCreate, ContactInfoResponse, ContactInfoUpdate
from app.service import contact_info_service

router = APIRouter(tags=["Contact Information"], prefix="/contact")


@router.post(
    "/",
    response_model=ContactInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create contact information",
)
async def create_contact_info(
    contact_data: ContactInfoCreate, session: dbSessionDep, current_store: CurrentStore
):
    return await contact_info_service.create(
        session, contact_data.model_dump(), current_store
    )


@router.get(
    "/{user_id}",
    response_model=ContactInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get contact information by user ID",
)
async def get_contact_info(current_store: CurrentStore):
    return await contact_info_service.get(current_store)


@router.put(
    "/",
    response_model=ContactInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Update contact information",
)
async def update_contact_info(
    contact_data: ContactInfoUpdate, session: dbSessionDep, current_store: CurrentStore
):
    return await contact_info_service.update(
        session, contact_data.model_dump(exclude_unset=True), current_store
    )


@router.delete(
    "/",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Delete contact information",
)
async def delete_contact_info(session: dbSessionDep, current_store: CurrentStore):
    return await contact_info_service.delete(session, current_store)
