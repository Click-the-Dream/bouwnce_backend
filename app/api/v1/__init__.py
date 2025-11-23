from fastapi import APIRouter, Depends

from app.api.v1 import (
    auth_router,
    cart_router,
    contact_info_crud,
    payout_info_crud,
    product_router,
    shipments_info_crud,
    store_crud,
    user_router,
    vendor_dashboard,
    verification_router,
    waitlist_router,
)
from app.core.rate_limiter import rate_limiter

user_api_router = APIRouter(
    prefix="/users",
    dependencies=[
        Depends(
            rate_limiter.rate_limit_dependency(
                ip_times=30, ip_seconds=60, user_times=100, user_seconds=60
            )
        )
    ],
)

user_api_router.include_router(cart_router.router)
user_api_router.include_router(user_router.router)
user_api_router.include_router(verification_router.router)


store_router = APIRouter(prefix="/store")

store_router.include_router(contact_info_crud.router)
store_router.include_router(payout_info_crud.router)
store_router.include_router(shipments_info_crud.router)
store_router.include_router(store_crud.router)
store_router.include_router(product_router.router)
store_router.include_router(vendor_dashboard.router)


waitlist = APIRouter(prefix="/waitlist")

waitlist.include_router(waitlist_router.router)

api_router = APIRouter()

api_router.include_router(auth_router.router)

api_router.include_router(user_api_router)
api_router.include_router(store_router)
api_router.include_router(waitlist)
