from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentActiveUser, redisSessionDep
import json

from app.utils.exception import NotFoundException
from app.worker.event_system import MOBILE_EVENTS_STREAM_KEY, PAYMENT_PROGRESS_KEY_PREFIX

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
    """
    Mobile clients should call repeatedly (or keep open) to receive events.
    Filter by `payload.user_id` client-side.
    """
    streams = await redis.xread(
        streams={MOBILE_EVENTS_STREAM_KEY: last_id},
        count=count,
        block=block_ms if block_ms > 0 else None,
    )

    items: list[dict] = []
    next_last_id = last_id

    for _stream_name, messages in streams or []:
        for msg_id, fields in messages:
            # fields are bytes->bytes with redis-py; decode safely
            decoded = {}
            for k, v in dict(fields).items():
                key = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
                val = v.decode() if isinstance(v, (bytes, bytearray)) else v
                decoded[key] = val

            items.append({"id": msg_id, **decoded})
            next_last_id = msg_id

    return {
        "status": "success",
        "items": items,
        "next_last_id": next_last_id,
    }


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
    key = f"{PAYMENT_PROGRESS_KEY_PREFIX}{reference}"
    value = await redis.get(key)
    if not value:
        raise NotFoundException("Payment progress not found (or expired)")
    if isinstance(value, (bytes, bytearray)):
        value = value.decode()
    try:
        data = json.loads(value)
    except Exception:
        data = {"raw": value}
    return {"status": "success", "data": data}
