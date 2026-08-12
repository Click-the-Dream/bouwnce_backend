from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status

from app.api.dependencies import CurrentActiveUser, dbSessionDep
from app.core.rate_limiter import rate_limiter
from app.schemas.web_push import (
    WebPushPublicKeyOut,
    WebPushSubscriptionIn,
    WebPushUnsubscribeIn,
)
from app.service.web_push_service import web_push_service
from app.utils.exception import BadRequestException, NotFoundException

router = APIRouter(prefix="/web-push", tags=["Web Push"])


@router.get(
    "/public-key",
    summary="Get the VAPID application server key used to subscribe to browser push",
    status_code=status.HTTP_200_OK,
    response_model=WebPushPublicKeyOut,
)
async def get_vapid_public_key() -> WebPushPublicKeyOut:
    return WebPushPublicKeyOut(
        enabled=web_push_service.enabled,
        public_key=web_push_service.public_key(),
    )


@router.post(
    "/subscriptions",
    summary="Register a browser push subscription for the current user",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    dependencies=[
        Depends(
            rate_limiter.rate_limit_dependency(
                ip_times=60, ip_seconds=60, user_times=20, user_seconds=60
            )
        )
    ],
)
async def subscribe_to_web_push(
    payload: WebPushSubscriptionIn,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    user_agent: str | None = Header(default=None),
) -> dict:
    if not web_push_service.enabled:
        raise BadRequestException("Web push is not configured on the server")
    await web_push_service.subscribe(
        db=db,
        user_id=str(current_user.id),
        subscription=payload,
        user_agent=user_agent,
    )
    return {"status": "success", "message": "Web push subscription saved"}


@router.delete(
    "/subscriptions",
    summary="Remove a browser push subscription for the current user",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def unsubscribe_from_web_push(
    payload: WebPushUnsubscribeIn,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
) -> dict:
    removed = await web_push_service.unsubscribe(
        db=db, user_id=str(current_user.id), endpoint=payload.endpoint
    )
    if not removed:
        raise NotFoundException("Web push subscription not found")
    return {"status": "success", "message": "Web push subscription removed"}
