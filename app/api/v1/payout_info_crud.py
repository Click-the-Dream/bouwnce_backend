from fastapi import APIRouter, status

from app.api.dependencies import CurrentStore, dbSessionDep
from app.schemas import (
    PayoutInfoCreate,
    PayoutInfoResponse,
    PayoutInfoUpdate,
)
from app.service import payout_info_service

router = APIRouter(tags=["Payout Information"], prefix="/payout")


@router.post(
    "/",
    response_model=PayoutInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create payout information",
)
async def create_payout_info(
    payout_data: PayoutInfoCreate, session: dbSessionDep, current_store: CurrentStore
):
    return await payout_info_service.create(
        session, payout_data.model_dump(), current_store
    )


@router.get(
    "/{user_id}",
    response_model=PayoutInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get payout information by user ID",
)
async def get_payout_info(current_store: CurrentStore):
    return await payout_info_service.get(current_store)


@router.put(
    "/",
    response_model=PayoutInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Update payout information",
)
async def update_payout_info(
    payout_data: PayoutInfoUpdate, session: dbSessionDep, current_store: CurrentStore
):
    return await payout_info_service.update(
        session, payout_data.model_dump(exclude_unset=True), current_store
    )


@router.delete(
    "/",
    response_model=dict,
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete payout information",
)
async def delete_payout_info(session: dbSessionDep, current_store: CurrentStore):
    return await payout_info_service.delete(session, current_store)
