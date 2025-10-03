from fastapi import APIRouter, Depends, status
from app.schemas import (
    BusinessInfoCreate,
    BusinessInfoUpdate,
    BusinessInfoResponse
)
from app.service import BusinessInfoCRUDService
from app.api.dependencies import dbSessionDep, CurrentStore

router = APIRouter(tags=["Business Information"], prefix="/business")

@router.post(
    "/", response_model=BusinessInfoResponse, status_code=status.HTTP_201_CREATED,
    summary="Create business information"
)
async def create_business_info(business_data: BusinessInfoCreate, session: dbSessionDep, current_store: CurrentStore):
    return await BusinessInfoCRUDService().create(session, business_data.dict(), current_store)

@router.get(
    "/{user_id}", response_model=BusinessInfoResponse, status_code=status.HTTP_200_OK,
    summary="Get business information by user ID"
)
async def get_business_info(current_store: CurrentStore):
    return await BusinessInfoCRUDService().get(current_store)

@router.put(
    "/", response_model=BusinessInfoResponse, status_code=status.HTTP_200_OK,
    summary="Update business information"
)
async def update_business_info(business_data: BusinessInfoUpdate, session: dbSessionDep, current_store: CurrentStore):
    return await BusinessInfoCRUDService().update(session, business_data.dict(), current_store)

@router.delete(
    "/", response_model=dict, status_code=status.HTTP_200_OK,
    summary="Delete business information"
)
async def delete_business_info(user_id: str, session: dbSessionDep):
    return await BusinessInfoCRUDService().delete(session, user_id)