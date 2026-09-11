from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentActiveUser, dbSessionDep
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.models.web_push_subscription import WebPushSubscription
from app.schemas.push_notification import PushSubscriptionIn, PushUnsubscribeIn
from app.service.web_push_service import get_vapid_public_key, send_web_push
from app.utils.exception import BadRequestException
from app.utils.responses import response_builder

router = APIRouter(prefix="/push", tags=["Push Notifications"])

MAX_SUBSCRIPTIONS_PER_USER = 10

subscribe_rate_limit = Depends(
    rate_limiter.rate_limit_dependency(
        ip_times=30, ip_seconds=60, user_times=60, user_seconds=60
    )
)


@router.get(
    "/vapid-public-key",
    summary="Get VAPID public key for browser subscription",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_vapid_public_key_endpoint() -> dict:
    public_key = get_vapid_public_key()
    if not public_key:
        raise BadRequestException("VAPID public key is not configured on the server")
    return response_builder(
        status_code=status.HTTP_200_OK,
        status="success",
        message="VAPID public key fetched successfully",
        data={"public_key": public_key},
    )


@router.post(
    "/subscribe",
    summary="Subscribe the current user's browser to web push",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    dependencies=[subscribe_rate_limit],
)
async def subscribe(
    data: PushSubscriptionIn,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
) -> dict:
    endpoint = data.endpoint

    existing = await WebPushSubscription.get_one(db, filter={"endpoint": endpoint})
    if existing is not None and str(existing.user_id) != str(current_user.id):
        # Never let one user claim/reassign another user's subscription row.
        raise BadRequestException(
            "This push subscription is already registered to another user"
        )
    if existing is None:
        current_count = len(
            await WebPushSubscription.list_for_user(db, current_user.id)
        )
        if current_count >= MAX_SUBSCRIPTIONS_PER_USER:
            raise BadRequestException(
                f"Push subscription limit reached "
                f"({MAX_SUBSCRIPTIONS_PER_USER} per user)"
            )

    await WebPushSubscription.upsert(
        db,
        user_id=current_user.id,
        endpoint=endpoint,
        p256dh=data.keys.p256dh,
        auth=data.keys.auth,
        expiration_time=data.expiration_time,
    )
    return response_builder(
        status_code=status.HTTP_200_OK,
        status="success",
        message="Push subscription saved",
        data={"endpoint": endpoint},
    )


@router.delete(
    "/subscribe",
    summary="Unsubscribe the current user's browser from web push",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    dependencies=[subscribe_rate_limit],
)
async def unsubscribe(
    data: PushUnsubscribeIn,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
) -> dict:
    removed = await WebPushSubscription.delete_by_endpoint(
        db, user_id=current_user.id, endpoint=data.endpoint
    )
    return response_builder(
        status_code=status.HTTP_200_OK,
        status="success",
        message=(
            "Push subscription removed" if removed else "Push subscription not found"
        ),
        data={"endpoint": data.endpoint, "removed": removed},
    )


@router.post(
    "/test",
    summary="Send a test push to the current user (dev only)",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    dependencies=[
        Depends(
            rate_limiter.rate_limit_dependency(
                ip_times=5, ip_seconds=60, user_times=10, user_seconds=60
            )
        )
    ],
)
async def send_test_push(
    db: dbSessionDep,
    current_user: CurrentActiveUser,
) -> dict:
    if settings.FASTAPI_ENV == "production":
        raise BadRequestException("Test push is not available in production")

    subscriptions = await WebPushSubscription.list_for_user(db, current_user.id)
    if not subscriptions:
        raise BadRequestException(
            "No web push subscription found. Subscribe first via POST /push/subscribe"
        )

    results = []
    for subscription in subscriptions:
        outcome = send_web_push(
            subscription,
            title="Bouwnce test push",
            body="This is a test notification from Bouwnce.",
            data={"type": "test"},
        )
        results.append(
            {
                "endpoint": subscription.endpoint,
                "delivered": outcome.delivered,
                "error": outcome.error,
            }
        )
        if outcome.expired:
            await WebPushSubscription.delete_by_endpoint(
                db, user_id=current_user.id, endpoint=subscription.endpoint
            )

    return response_builder(
        status_code=status.HTTP_200_OK,
        status="success",
        message="Test push sent",
        data={"results": results},
    )
