from fastapi import APIRouter, Depends, status
from app.schemas import (
    StoreInfoCreate,
    StoreInfoUpdate,
    StoreInfoResponse
)
from app.service import StoreInfoCRUDService
from app.api.dependencies import dbSessionDep, CurrentStore
from typing import Any
from app.db.postgres_db_conn import get_async_session


router = APIRouter(tags=["Store Information"], prefix="/store_info")

@router.post(
    "/", response_model=StoreInfoResponse, status_code=status.HTTP_201_CREATED, 
    summary="Create store information"
)
async def create_store_info(store_data: StoreInfoCreate, session: dbSessionDep, current_store: CurrentStore):
    return await StoreInfoCRUDService().create(session, store_data.dict(), current_store)

@router.get(
    "/{user_id}", response_model=StoreInfoResponse, status_code=status.HTTP_200_OK,
    summary="Get store information by user ID"
)
async def get_store_info(current_store: CurrentStore):
    return await StoreInfoCRUDService().get(current_store)

@router.put(
    "/", response_model=StoreInfoResponse, status_code=status.HTTP_200_OK,
    summary="Update store information"
)
async def update_store_info(store_data: StoreInfoUpdate, session: dbSessionDep, current_store: CurrentStore):
    return await StoreInfoCRUDService().update(session, store_data.dict(), current_store)

@router.delete(
    "/", response_model=dict, status_code=status.HTTP_200_OK,
    summary="Delete store information"
)
async def delete_store_info(session: dbSessionDep, current_store: CurrentStore):
    return await StoreInfoCRUDService().delete(session, current_store)