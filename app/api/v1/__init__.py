from fastapi import APIRouter

from app.api.v1 import (
    auth_router,
    cart_router,
    contact_info_crud,
    payout_info_crud,
    product_router,
    shipments_info_crud,
    store_crud,
    store_info_crud,
    user_router,
    verification_router,
    vendor_dashboard,
)

user_api_router = APIRouter(prefix="/users")

user_api_router.include_router(cart_router.router)
user_api_router.include_router(user_router.router)
user_api_router.include_router(verification_router.router)


store_router = APIRouter(prefix="/store")

store_router.include_router(contact_info_crud.router)
store_router.include_router(payout_info_crud.router)
store_router.include_router(store_info_crud.router)
store_router.include_router(shipments_info_crud.router)
store_router.include_router(store_crud.router)

vendor_dashboard_router = APIRouter(prefix="/vendor/dashboard")
vendor_dashboard_router.include_router(vendor_dashboard.router)

api_router = APIRouter()

api_router.include_router(auth_router.router)
api_router.include_router(product_router.router)
api_router.include_router(user_api_router)
api_router.include_router(store_router)
