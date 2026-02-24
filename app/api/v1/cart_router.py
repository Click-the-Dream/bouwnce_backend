from fastapi import APIRouter, status
from fastapi.requests import Request

from app.api.dependencies import CurrentActiveUser, dbSessionDep, redisSessionDep
from app.schemas.cart import (
    CartCreate,
    CartResponse,
    CheckoutResponse,
    PaginatedCartResponse,
    UpdateCart,
)
from app.schemas.order import CheckoutInputSchema
from app.schemas.shipments_info_crud import StoreShipmentsInfoResponse
from app.service.cart_service import cart_service
from app.service.order_srevice import order_service

router = APIRouter(prefix="/carts", tags=["Carts"])


@router.post(
    "/",
    summary="Create a new cart for user",
    status_code=status.HTTP_201_CREATED,
    response_model=CartResponse,
)
async def create_cart(
    cart_data: CartCreate, current_user: CurrentActiveUser, db: dbSessionDep
):
    cart_data = cart_data.model_dump()
    cart_data["user_id"] = current_user.id

    return await cart_service.create(cart_data, db)


@router.get(
    "/",
    summary="Get all user carts",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedCartResponse,
)
async def get_all_user_carts(
    current_user: CurrentActiveUser,
    db: dbSessionDep,
    page: int | None = 1,
    page_size: int | None = 10,
):
    return await cart_service.get_all_by_user(str(current_user.id), db, page, page_size)


@router.get(
    "/cart-shipping-info",
    summary="Get cart shipping info",
    response_model=StoreShipmentsInfoResponse,
)
async def get_cart_shipping_info(current_user: CurrentActiveUser, db: dbSessionDep):
    return await order_service.get_cart_shipping_info(current_user, db)


@router.get(
    "/{id}",
    summary="Get a cart with Id",
    status_code=status.HTTP_200_OK,
    response_model=CartResponse,
)
async def get_cart_by_id(id: str, current_user: CurrentActiveUser, db: dbSessionDep):
    return await cart_service.get_by_id(id, db)


@router.put(
    "/{id}",
    summary="Update a cart with id",
    status_code=status.HTTP_200_OK,
    response_model=CartResponse,
)
async def update_cart(
    id: str, update_data: UpdateCart, current_user: CurrentActiveUser, db: dbSessionDep
):
    return await cart_service.update(
        user_id=current_user.id, cart_id=id, update_data=update_data.model_dump(), db=db
    )


@router.delete(
    "/{id}", summary="Delete a cart by Id", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_cart_by_id(id: str, current_user: CurrentActiveUser, db: dbSessionDep):
    return await cart_service.delete(user_id=current_user.id, cart_id=id, db=db)


@router.delete(
    "/", summary="Delete all cart for a user", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_all_user_cart(current_user: CurrentActiveUser, db: dbSessionDep):
    return await cart_service.delete_all_user_cart(current_user.id, db)


@router.post(
    "/checkout",
    summary="Checkout current user cart",
    status_code=status.HTTP_200_OK,
    response_model=CheckoutResponse,
)
async def checkout_cart(
    shipment_list: list[CheckoutInputSchema],
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    request: Request,
    redis: redisSessionDep,
):
    return await order_service.checkout(
        user=current_user, redis=redis, request=request, db=db
    )
