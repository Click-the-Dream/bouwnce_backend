from fastapi import APIRouter, status

from app.api.dependencies import CurrentStore, CurrentVendor, dbSessionDep
from app.schemas import BusinessInfoCreate, BusinessInfoResponse, BusinessInfoUpdate
from app.service import business_service

router = APIRouter(tags=["Business Information"], prefix="/business")


@router.post(
    "/",
    response_model=BusinessInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create business information",
)
async def create_business_info(
    business_data: BusinessInfoCreate,
    session: dbSessionDep,
    current_vendor: CurrentVendor,
):
    return await business_service.create(
        session, business_data.model_dump(), current_vendor
    )


@router.get(
    "/{user_id}",
    response_model=BusinessInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get business information by user ID",
)
async def get_business_info(current_store: CurrentStore):
    return await business_service.get(current_store)


@router.put(
    "/",
    response_model=BusinessInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Update business information",
)
async def update_business_info(
    business_data: BusinessInfoUpdate,
    session: dbSessionDep,
    current_store: CurrentStore,
):
    return await business_service.update(
        session, business_data.model_dump(exclude_unset=True), current_store
    )


@router.delete(
    "/",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Delete business information",
)
async def delete_business_info(session: dbSessionDep, current_store: CurrentStore):
    return await business_service.delete(session, current_store)
