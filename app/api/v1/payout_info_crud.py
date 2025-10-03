from fastapi import APIRouter, Depends, status
from app.schemas import (
    PayoutInfoCreate,
    PayoutInfoUpdate,
    PayoutInfoResponse,
)
from app.service import PayoutInfoCRUDService
from app.api.dependencies import dbSessionDep, CurrentStore


router = APIRouter(tags=["Payout Information"], prefix="/payout")

@router.post(
    "/", response_model=PayoutInfoResponse, status_code=status.HTTP_201_CREATED,
    summary="Create payout information"
)
async def create_payout_info(payout_data: PayoutInfoCreate, session: dbSessionDep, current_store: CurrentStore):
    return await PayoutInfoCRUDService().create(session, payout_data.dict(), current_store)

@router.get(
    "/{user_id}", response_model=PayoutInfoResponse, status_code=status.HTTP_200_OK,
    summary="Get payout information by user ID"
)
async def get_payout_info(current_store: CurrentStore):
    return await PayoutInfoCRUDService().get(session, user_id, current_store)

@router.put(
    "/", response_model=PayoutInfoResponse, status_code=status.HTTP_200_OK,
    summary="Update payout information"
)
async def update_payout_info(payout_data: PayoutInfoUpdate, session: dbSessionDep, current_store: CurrentStore):
    return await PayoutInfoCRUDService().update(session, payout_data.dict(), current_store)

@router.delete(
    "/", response_model=dict, status_code=status.HTTP_200_OK,
    summary="Delete payout information"
)
async def delete_payout_info(user_id: str, session: dbSessionDep):
    return await PayoutInfoCRUDService().delete(session, user_id)