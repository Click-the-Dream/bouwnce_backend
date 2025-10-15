from typing import Any

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    CurrentActiveStore,
    CurrentStore,
    CurrentUser,
    dbSessionDep,
)
from app.schemas import (
    StoreCreate,
    StoreFullDetailsResponse,
    StoreResponse,
    StoreUpdate,
)
from app.service import store_service

router = APIRouter(tags=["Store"], prefix="")


@router.post(
    "/",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create store information",
)
async def create_store(
    store_data: StoreCreate, session: dbSessionDep, current_user: CurrentUser
):
    return await store_service.create(session, store_data.model_dump(), current_user)


@router.get(
    "/",
    response_model=StoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all Available with search filters (name)",
)
async def get_stores(
    db: dbSessionDep,
    name: str | None = Query(default=None, description="Search Query"),
    page: int | None = Query(default=1, description="The page to fetch"),
    page_sze: int | None = Query(
        default=10, description="The number of stores per page"
    ),
):
    return await store_service.get_stores(
        db=db, name=name, page=page, page_size=page_sze
    )


@router.get(
    "/my-store",
    response_model=StoreFullDetailsResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Current Store full details including (business_info, payment_info, etc)",
)
async def get_store_full_details(current_store: CurrentStore):
    return await store_service.get_full_details(current_store)


@router.get(
    "/{vendor_id}",
    response_model=StoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Get store rmation by user ID",
)
async def get_store_by_id(vendor_id: str, db: dbSessionDep):
    return await store_service.get_vendor_store(vendor_id, db)


@router.put(
    "/",
    response_model=StoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Update store rmation",
)
async def update_store(
    store_data: StoreUpdate, session: dbSessionDep, current_store: CurrentActiveStore
):
    return await store_service.update(
        session, store_data.model_dump(exclude_unset=True), current_store
    )


@router.put(
    "/deactivate",
    response_model=StoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate Store account",
)
async def deactivate_store(current_store: CurrentActiveStore, db: dbSessionDep):
    return await store_service.deactivate(db, current_store)


@router.put(
    "/activate",
    response_model=StoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate Store account",
)
async def activate_store(current_store: CurrentActiveStore, db: dbSessionDep):
    return await store_service.activate(db, current_store)


@router.delete(
    "/",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Delete store rmation",
)
async def delete_store(session: dbSessionDep, current_store: CurrentActiveStore):
    return await store_service.delete(session, current_store)
