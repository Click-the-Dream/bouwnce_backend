from fastapi import APIRouter, status

from app.api.dependencies import CurrentActiveUser, dbSessionDep
from app.service.order_srevice import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.patch(
    "/items/{order_item_id}/cancel",
    summary="Cancel an order item",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def cancel_order_item(
    order_item_id: str,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
):
    return await order_service.cancel_order(
        order_item_id=order_item_id,
        db=db,
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
    current_user: CurrentActiveUser,
):
    return await order_service.accept_order(
        order_item_id=order_item_id,
        db=db,
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
    current_user: CurrentActiveUser,
):
    return await order_service.complete_order(
        order_id=order_id,
        db=db,
        current_user=current_user,
    )
