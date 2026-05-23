from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from app.api.dependencies import (
    CurrentActiveUser,
    CurrentVendor,
    dbSessionDep,
    redisSessionDep,
)
from app.service.order_srevice import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


class SubOrderStatusUpdatePayload(BaseModel):
    status: str = Field(
        ...,
        description="New suborder status",
        examples=["shipped"],
    )


@router.patch(
    "/items/{order_item_id}/cancel",
    summary="Cancel an order item",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def cancel_order_item(
    order_item_id: str,
    db: dbSessionDep,
    redis: redisSessionDep,
    current_user: CurrentActiveUser,
):
    return await order_service.cancel_order(
        order_item_id=order_item_id,
        db=db,
        redis=redis,
        current_user=current_user,
    )


@router.patch(
    "/items/{order_item_id}/accept",
    summary="Accept an order item",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def accept_order_item(
    order_item_id: str,
    db: dbSessionDep,
    redis: redisSessionDep,
    current_user: CurrentActiveUser,
):
    return await order_service.accept_order(
        order_item_id=order_item_id,
        db=db,
        redis=redis,
        current_user=current_user,
    )


@router.patch(
    "/items/{order_item_id}/decline",
    summary="Decline an order item (vendor)",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def decline_order_item(
    order_item_id: str,
    db: dbSessionDep,
    redis: redisSessionDep,
    current_user: CurrentVendor,
):
    return await order_service.decline_order_item(
        order_item_id=order_item_id,
        db=db,
        redis=redis,
        current_user=current_user,
    )


@router.patch(
    "/{order_id}/complete",
    summary="Mark an order as completed",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def complete_order(
    order_id: str,
    db: dbSessionDep,
    redis: redisSessionDep,
    current_user: CurrentActiveUser,
):
    return await order_service.complete_order(
        order_id=order_id,
        db=db,
        redis=redis,
        current_user=current_user,
    )


@router.get(
    "",
    summary="List buyer orders (paginated)",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def list_my_orders(
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    return await order_service.fetch_user_orders(
        user_id=str(current_user.id),
        db=db,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{order_id}",
    summary="Get buyer order by id",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_my_order_by_id(
    order_id: str,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
):
    return await order_service.fetch_user_order_by_id(order_id=order_id, db=db)


@router.get(
    "/track/{track_id}",
    summary="Get buyer order by track id",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_my_order_by_track_id(
    track_id: str,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
):
    return await order_service.fetch_user_order_by_track_id(track_id=track_id, db=db)


@router.patch(
    "/suborders/{suborder_id}/status",
    summary="Vendor update suborder status",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def update_suborder_status(
    suborder_id: str,
    db: dbSessionDep,
    redis: redisSessionDep,
    current_user: CurrentVendor,
    payload: SubOrderStatusUpdatePayload,
):
    return await order_service.update_suborder_status(
        suborder_id=suborder_id,
        new_status=payload.status,
        db=db,
        redis=redis,
        current_user=current_user,
    )
