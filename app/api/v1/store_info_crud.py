from fastapi import APIRouter, status

from app.api.dependencies import CurrentStore, dbSessionDep
from app.schemas import StoreInfoCreate, StoreInfoResponse, StoreInfoUpdate
from app.service import store_info_service

router = APIRouter(tags=["Store Information"], prefix="/store_info")


@router.post(
    "/",
    response_model=StoreInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create store information",
)
async def create_store_info(
    store_data: StoreInfoCreate, session: dbSessionDep, current_store: CurrentStore
):
    return await store_info_service.create(
        session, store_data.model_dump(), current_store
    )


@router.get(
    "/{user_id}",
    response_model=StoreInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get store information by user ID",
)
async def get_store_info(current_store: CurrentStore):
    return await store_info_service.get(current_store)


@router.put(
    "/",
    response_model=StoreInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Update store information",
)
async def update_store_info(
    store_data: StoreInfoUpdate, session: dbSessionDep, current_store: CurrentStore
):
    return await store_info_service.update(
        session, store_data.model_dump(exclude_unset=True), current_store
    )


@router.delete(
    "/",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Delete store information",
)
async def delete_store_info(session: dbSessionDep, current_store: CurrentStore):
    return await store_info_service.delete(session, current_store)
