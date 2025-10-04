from fastapi import APIRouter, status
from app.schemas import (
    StoreCreate,
    StoreUpdate,
    StoreResponse
)
from app.service import StoreCRUDService
from app.api.dependencies import dbSessionDep, CurrentUser, CurrentStore
from typing import Any

router = APIRouter(tags=["Store"], prefix="/store")

@router.post(    
    "/", response_model=StoreResponse, status_code=status.HTTP_201_CREATED,
    summary="Create store information"
)
async def create_store(store_data: StoreCreate, session: dbSessionDep, current_user: CurrentUser):
    return await StoreCRUDService().create(session, store_data.dict(), current_user)

@router.get(
    "/{user_id}", response_model=StoreResponse, status_code=status.HTTP_200_OK,
    summary="Get store rmation by user ID"
)
async def get_store(current_store: CurrentStore):
    return await StoreCRUDService().get(current_store)

@router.put(
    "/", response_model=StoreResponse, status_code=status.HTTP_200_OK,
    summary="Update store rmation"
)
async def update_store(store_data: StoreUpdate, session: dbSessionDep, current_store: CurrentStore):
    return await StoreCRUDService().update(session, store_data.dict(), current_store)   

@router.delete(
    "/", response_model=dict[str, Any], status_code=status.HTTP_200_OK,
    summary="Delete store rmation"
)
async def delete_store(session: dbSessionDep, current_store: CurrentStore):
    return await StoreCRUDService().delete(session, current_store)