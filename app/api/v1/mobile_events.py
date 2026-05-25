from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, status

from app.api.dependencies import CurrentActiveUser, redisSessionDep
from app.api.dependencies import dbSessionDep
from app.service.mobile_events_service import mobile_events_service

router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "/mobile",
    summary="Read mobile events from Redis Stream (long-poll)",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def read_mobile_events(
    redis: redisSessionDep,
    current_user: CurrentActiveUser,
    last_id: str = Query(
        "0-0",
        description="Last Redis stream id received. Use returned `next_last_id` for the next call.",
    ),
    block_ms: int = Query(25000, ge=0, le=60000),
    count: int = Query(50, ge=1, le=200),
) -> dict:
    return await mobile_events_service.read_mobile_events(
        redis=redis,
        user_id=str(current_user.id),
        last_id=last_id,
        block_ms=block_ms,
        count=count,
    )


@router.get(
    "/payments/progress",
    summary="Get latest payment progress snapshot",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_payment_progress(
    redis: redisSessionDep,
    current_user: CurrentActiveUser,
    reference: str = Query(..., min_length=3),
) -> dict:
    _ = current_user
    return await mobile_events_service.get_payment_progress(redis=redis, reference=reference)


@router.get(
    "/unread",
    summary="Get unread chat + notification summary",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_unread_summary(
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    data = await mobile_events_service.get_unread_summary(
        db=db, user_id=str(current_user.id), page_size=page_size
    )
    return {"status": "success", "data": data}


@router.websocket("/ws")
async def events_ws(websocket: WebSocket) -> None:
    await mobile_events_service.handle_ws(websocket)
