from fastapi import APIRouter, Depends

from app.api.v1 import (
    auth_router,
    cart_router,
    contact_info_crud,
    jobs,
    mobile_events,
    newsletter,
    order_router,
    payment,
    payout_info_crud,
    product_router,
    shipments_info_crud,
    store_crud,
    uploads,
    user_router,
    vendor_dashboard,
    verification_router,
    waitlist_router,
)
from app.core.rate_limiter import rate_limiter
from app.matching_ground.api.rest import chat, interest, location, match
from app.utils.responses import (
    BadRequestResponse,
    ForbiddenResponse,
    InternalServerErrorResponse,
    NotFoundResponse,
    UnauthorizedResponse,
)

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
user_api_router.include_router(order_router.router)
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

api_router.include_router(
    auth_router.router,
    responses={
        400: {"model": BadRequestResponse},
        401: {"model": UnauthorizedResponse},
        403: {"model": ForbiddenResponse},
        404: {"model": NotFoundResponse},
        500: {"model": InternalServerErrorResponse},
    },
)


api_router.include_router(user_api_router)
api_router.include_router(store_router)
api_router.include_router(waitlist)
api_router.include_router(payment.router)
api_router.include_router(newsletter.router)
api_router.include_router(jobs.router)
api_router.include_router(interest.router)
api_router.include_router(match.router)
api_router.include_router(location.router)
api_router.include_router(mobile_events.router)
api_router.include_router(uploads.router)
api_router.include_router(chat.router)
