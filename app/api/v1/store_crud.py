from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.dependencies import (
    CurrentActiveStore,
    CurrentStore,
    CurrentUser,
    dbSessionDep,
)
from app.schemas.store_crud import (
    PaginatStoreResponse,
    StoreCreate,
    StoreFullDetailsResponse,
    StoreResponse,
    StoreUpdate,
)
from app.service import store_service
from app.utils.responses import BaseResponse

ImageUpdate = Annotated[UploadFile | None, File(...)]

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
    response_model=PaginatStoreResponse,
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
    "/onboarding-status",
    status_code=status.HTTP_200_OK,
    summary="Get Current Store onboarding status",
    response_model=BaseResponse,
)
async def get_store_onboarding_status(current_store: CurrentStore):
    return await store_service.get_store_onboarding_status(current_store)


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
    "/branding",
    response_model=StoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Store branding",
)
async def update_store_brand(
    db: dbSessionDep,
    current_store: CurrentActiveStore,
    store_logo: ImageUpdate = None,
    store_banner: ImageUpdate = None,
    store_description: Annotated[
        str | None, Form(min_length=10, examples=["The best Cloth store"])
    ] = None,
):
    return await store_service.update_store_branding(
        current_store, db, store_description, store_logo, store_banner
    )


@router.put(
    "/deactivate",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate Store account",
)
async def deactivate_store(current_store: CurrentActiveStore, db: dbSessionDep):
    return await store_service.deactivate(db, current_store)


@router.put(
    "/activate",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate Store account",
)
async def activate_store(current_store: CurrentActiveStore, db: dbSessionDep):
    return await store_service.activate(db, current_store)


@router.delete(
    "/",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete store rmation",
)
async def delete_store(session: dbSessionDep, current_store: CurrentActiveStore):
    return await store_service.delete(session, current_store)


@router.delete(
    "/brand-image",
    status_code=status.HTTP_200_OK,
    summary="delete Store brand logo or banner",
    response_model=BaseResponse,
)
async def delete_store_brand_images(
    db: dbSessionDep,
    current_store: CurrentActiveStore,
    del_store_logo: bool | None = Query(
        default=None, description="Delete store logo image"
    ),
    del_store_banner: bool | None = Query(
        default=None, description="Delete store banner image"
    ),
):
    return await store_service.delete_brand_images(
        db, current_store, del_store_logo, del_store_banner
    )
