from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.dependencies import CurrentActiveUser, redisSessionDep

from app.core.security import verify_token
from app.utils.exception import NotFoundException
from app.core.config import MOBILE_EVENTS_STREAM_KEY, PAYMENT_PROGRESS_KEY_PREFIX
from app.db.redis import get_redis_client
from app.db.postgres_db_conn import get_async_session
from app.models.user import User
from app.matching_ground.schema.chat import MarkConversationReadPayload, SendMessagePayload
from app.matching_ground.service.chat_service import chat_service

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


@router.websocket("/ws")
async def events_ws(websocket: WebSocket) -> None:
    """
    One websocket for multiple realtime states:
    - Chat: Redis PubSub channel `chat:user:{user_id}`
    - Events: Redis Stream `events:mobile:stream` (filtered by payload.user_id)

    Connect:
      `wss://<domain>/api/v1/events/ws?token=<access_token>`

    Send chat messages over the same socket:
      `{"type":"chat.send","recipient_id":"<uuid>","body":"hi"}`

    Mark a conversation as read (by other user id):
      `{"type":"chat.read","conversation_id":"<uuid>","message_id":"<uuid>"}`
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    token_payload = verify_token(token)
    if token_payload.get("type") != "access":
        await websocket.close(code=1008)
        return

    user_id = token_payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return

    redis = await get_redis_client()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"chat:user:{user_id}")

    await websocket.accept()

    async def forward_pubsub() -> None:
        try:
            async for msg in pubsub.listen():
                if msg is None:
                    continue
                if msg.get("type") != "message":
                    continue
                data = msg.get("data")
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode()
                # Chat service publishes JSON strings; forward as JSON when possible
                try:
                    await websocket.send_json(json.loads(data))
                except Exception:
                    await websocket.send_text(str(data))
        except Exception:
            return

    async def forward_stream() -> None:
        last_id = "$"
        try:
            while True:
                streams = await redis.xread(
                    streams={MOBILE_EVENTS_STREAM_KEY: last_id}, count=50, block=25000
                )
                for _stream_name, messages in streams or []:
                    for msg_id, fields in messages:
                        last_id = msg_id
                        event_name = fields.get("event_name")
                        payload_raw = fields.get("payload")
                        if not event_name or not payload_raw:
                            continue
                        try:
                            payload_obj = json.loads(payload_raw)
                        except Exception:
                            continue
                        if str(payload_obj.get("user_id") or "") != str(user_id):
                            continue
                        await websocket.send_json(
                            {
                                "type": "event",
                                "event_name": event_name,
                                "payload": payload_obj,
                            }
                        )
        except Exception:
            return

    pubsub_task = asyncio.create_task(forward_pubsub())
    stream_task = asyncio.create_task(forward_stream())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                incoming = json.loads(raw)
            except Exception:
                # Ignore non-JSON payloads
                continue

            msg_type = str(incoming.get("type") or "").strip().lower()
            if not msg_type:
                continue

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "chat.send":
                try:
                    payload = SendMessagePayload.model_validate(incoming)
                except Exception:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": "invalid_payload",
                            "message": "Expected: {type:'chat.send', recipient_id:'<uuid>', body:'...'}",
                        }
                    )
                    continue

                async with get_async_session() as db:
                    sender = await User.get_by_id(str(user_id), db)
                    result = await chat_service.send_message(
                        db=db,
                        redis=redis,
                        sender=sender,
                        recipient_id=payload.recipient_id,
                        body=payload.body,
                        commit=False,
                        as_response=False,
                    )

                await websocket.send_json({"type": "chat.sent", "data": result})
                continue

            if msg_type == "chat.read":
                try:
                    payload = MarkConversationReadPayload.model_validate(incoming)
                except Exception:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": "invalid_payload",
                            "message": "Expected: {type:'chat.read', conversation_id:'<uuid>', message_id:'<uuid>'}",
                        }
                    )
                    continue

                async with get_async_session() as db:
                    result = await chat_service.mark_conversation_read_up_to_message(
                        db=db,
                        redis=redis,
                        current_user_id=str(user_id),
                        conversation_id=str(payload.conversation_id),
                        message_id=str(payload.message_id),
                        commit=False,
                        as_response=False,
                    )

                await websocket.send_json({"type": "chat.read.ack", "data": result})
                continue
    except WebSocketDisconnect:
        pass
    finally:
        pubsub_task.cancel()
        stream_task.cancel()
        await pubsub.unsubscribe(f"chat:user:{user_id}")
        await pubsub.close()
